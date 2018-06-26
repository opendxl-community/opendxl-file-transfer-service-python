from __future__ import absolute_import
import hashlib
import logging
import os
import shutil
import threading
import uuid

from dxlclient.callbacks import RequestCallback
from dxlclient.message import Response, ErrorResponse
from dxlbootstrap.util import MessageUtils
from .constants import FileStoreProp, FileStoreResultProp

# Configure local logger
logger = logging.getLogger(__name__)


def _get_value_as_int(dict_obj, key):
    """
    Return the value associated with a key in a dictionary, converted to an int.

    :param dict dict_obj: Dictionary to retrieve the value from
    :param str key: Key associated with the value to return
    :return The value, as an integer. Returns 'None' if the key cannot be found
        in the dictionary.
    :rtype: int
    :raises ValueError: If the key is present in the dictionary but the value
        cannot be converted to an int.
    """
    return_value = None
    if key in dict_obj:
        try:
            return_value = int(dict_obj.get(key))
        except ValueError:
            raise ValueError(
                "'{}' of '{}' could not be converted to an int".format(
                    key, return_value))
    return return_value


class FileStoreRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_store' request handler registered with topic
    '/opendxl-file-transfer/service/file/store'
    """

    #: "Working" subdirectory under the primary storage directory which can
    #: contain temporary files related to file storage operations.
    _STORAGE_WORK_SUBDIR = ".workdir"

    #: Key name for tracking a file hash (SHA-256 only for now)
    _FILE_HASHER = "file_hasher"

    #: Key name containing the name of the directory under which a file is
    #: stored.
    _FILE_DIR = "dir"

    #: Key name containing the full path to a file to be stored.
    _FILE_FULL_PATH = "full_path"

    def __init__(self, app, storage_dir):
        """
        Constructor parameters:

        :param dxlfiletransferservice.app.FileTransferService app: The
            application this handler is associated with
        :param str storage_dir: Directory under which files are stored
        """
        super(FileStoreRequestCallback, self).__init__()
        self._app = app
        self._files = {}
        self._files_lock = threading.RLock()

        self._storage_work_dir = os.path.join(storage_dir,
                                              self._STORAGE_WORK_SUBDIR)
        if not os.path.exists(self._storage_work_dir):
            os.makedirs(self._storage_work_dir)

        logger.info("Using file store at '%s'", os.path.abspath(storage_dir))
        self._storage_dir = storage_dir
        self._purge_incomplete_files()

    def _purge_incomplete_files(self):
        """
        Purge working files for file storage operations which did not complete
        successfully.
        """
        for incomplete_file_id in os.listdir(self._storage_work_dir):
            logger.info("Purging content for incomplete file id: '{}'".format(
                incomplete_file_id
            ))
            file_path = os.path.join(self._storage_dir, incomplete_file_id)
            if os.path.exists(file_path):
                shutil.rmtree(file_path)
            os.remove(os.path.join(self._storage_work_dir, incomplete_file_id))

    def _write_file_segment(self, file_entry, segment):
        """
        Write the supplied segment to the file associated with the supplied
        file_entry.

        :param dict file_entry: Dictionary containing file information.
        :param bytes segment: Bytes of the segment to write to a file.
        """
        segments_received = file_entry[FileStoreProp.SEGMENTS_RECEIVED]
        logger.debug("Storing segment '%d' for file id: '%s'",
                     segments_received, file_entry[FileStoreProp.ID])
        with open(file_entry[self._FILE_FULL_PATH], "ab+") as file_handle:
            if segment:
                file_handle.write(segment)
                file_entry[self._FILE_HASHER].update(segment)
        file_entry[FileStoreProp.SEGMENTS_RECEIVED] = segments_received

    @staticmethod
    def _get_requested_file_result(params, file_id, file_size, file_hash):
        """
        Extract the value of the requested file result from the supplied
        params dictionary.

        :param dict params: The dictionary
        :param str file_id: A file id.
        :param int file_size: A file size.
        :param str file_hash: A file hash
        :return: The requested file result. If the result is not available
            in the dictionary, 'None' is returned.
        :rtype: str
        :raises ValueError: If the file id, size, and/or hash parameter
            values are not appropriate for the requested file result
        """
        requested_file_result = params.get(FileStoreProp.RESULT)
        if requested_file_result:
            if requested_file_result == FileStoreResultProp.CANCEL:
                if not file_id:
                    raise ValueError("File id to cancel must be specified")
            elif requested_file_result == FileStoreResultProp.STORE:
                if file_size is None:
                    raise ValueError(
                        "File size must be specified for store request")
                if file_size is not None and not file_hash:
                    raise ValueError(
                        "File hash must be specified for store request")
            else:
                raise ValueError(
                    "Unexpected '{}' value: '{}'".
                    format(FileStoreProp.RESULT, requested_file_result))
        return requested_file_result

    def _get_file_entry(self, file_id, file_name):
        """
        Get file entry information for the supplied id.

        :param str file_id: Id of the file associated with the entry. If 'None',
            a new entry is created.
        :param str file_name: Name to store in a newly-created file entry.
        :return: Dictionary containing information for the file entry.
        :rtype: dict
        """
        if file_id:
            with self._files_lock:
                file_entry = self._files.get(file_id)
                if not file_entry:
                    raise ValueError(
                        "Unable to find file id: {}".format(file_id))
        else:
            file_id = str(uuid.uuid4()).lower()
            with open(os.path.join(self._storage_work_dir, file_id), "w"):
                pass
            file_dir = os.path.join(self._storage_dir, file_id)
            os.makedirs(file_dir)
            file_entry = {
                FileStoreProp.ID: file_id,
                FileStoreProp.NAME: file_name,
                FileStoreProp.SEGMENTS_RECEIVED: 0,
                self._FILE_HASHER: hashlib.sha256(),
                self._FILE_DIR: file_dir,
                self._FILE_FULL_PATH: os.path.join(file_dir, file_name)
            }
            with self._files_lock:
                self._files[file_id] = file_entry
            logger.info("Assigning file id '%s' for '%s'", file_id,
                        file_entry[self._FILE_FULL_PATH])
        return file_entry

    def _complete_file(self, file_entry, requested_file_result,
                       last_segment, file_size, file_hash):
        """
        Complete the storage operation for a file entry.

        :param dict file_entry: The entry of the file to complete.
        :param str requested_file_result: The desired storage result. If the
            value is :const:`FileStoreResultProp.STORE` but the expected
            size/hash does not match the stored size/hash or if the value
            is :const:`FileStoreResultProp.CANCEL`, the stored file
            contents are removed from disk.
        :param bytes last_segment: The last segment of the file to be stored.
            This may be 'None'. The last segment is not written if the
            requested_file_result is set to
            :const:`FileStoreResultProp.CANCEL`.
        :param int file_size: Expected size of the stored file.
        :param str file_hash: Expected SHA-256 hexstring hash of the contents of
            the stored file
        :return: The value of the requested_file_result.
        :raises ValueError: If the stored size/hash does not match the
            expected size/hash for the file.
        :rtype: str
        """
        file_id = file_entry[FileStoreProp.ID]
        file_dir = file_entry[self._FILE_DIR]
        full_file_path = file_entry[self._FILE_FULL_PATH]

        workdir_file = os.path.join(self._storage_work_dir, file_id)
        if os.path.exists(workdir_file):
            os.remove(workdir_file)

        if requested_file_result == FileStoreResultProp.STORE:
            store_error = None
            self._write_file_segment(file_entry, last_segment)
            stored_file_size = os.path.getsize(full_file_path)
            if stored_file_size != file_size:
                store_error = "Unexpected file size. Expected: '" + \
                              str(stored_file_size) + "'. Received: '" + \
                              str(file_size) + "'."
            if stored_file_size:
                stored_file_hash = file_entry[
                    self._FILE_HASHER].hexdigest()
                if stored_file_hash != file_hash:
                    store_error = "Unexpected file hash. Expected: " + \
                                  "'" + str(stored_file_hash) + \
                                  "'. Received: '" + \
                                  str(file_hash) + "'."
            if store_error:
                shutil.rmtree(file_dir)
                raise ValueError(
                    "File storage error for file '%s': %s".format(
                        file_id, store_error))
            logger.info("Stored file '%s' for id '%s'", full_file_path,
                        file_id)
            result = FileStoreResultProp.STORE
        else:
            shutil.rmtree(file_dir)
            logger.info("Canceled storage of file for id '%s'", file_id)
            result = FileStoreResultProp.CANCEL

        return result

    def _process_store_request(self, file_entry, segment, segment_number,
                               requested_file_result, file_size, file_hash):
        """
        Process a store request. If the request contains a file segment, the
        segment is written to disk.

        :param dict file_entry: The entry of the file to process.
        :param bytes segment: A segment to be stored for the file.
        :param int segment_number: The sequence number for the associated
            segment.
        :param str requested_file_result: The desired storage result. If the
            value is :const:`FileStoreResultProp.STORE` but the expected
            size/hash does not match the stored size/hash or if the value
            is :const:`FileStoreResultProp.CANCEL`, the stored file
            contents are removed from disk.
        :param int file_size: Expected size of the stored file.
        :param str file_hash: Expected SHA-256 hexstring hash of the contents of
            the stored file
        :return:
        """
        result = {FileStoreProp.ID: file_entry[FileStoreProp.ID]}

        if requested_file_result != FileStoreResultProp.CANCEL:
            segments_received = file_entry[
                FileStoreProp.SEGMENTS_RECEIVED]
            if (segments_received + 1) == segment_number:
                file_entry[FileStoreProp.SEGMENTS_RECEIVED] = \
                    segments_received + 1
            else:
                raise ValueError(
                    "Unexpected segment. Expected: '{}'. Received: '{}'".
                    format(segments_received + 1, segment_number))

        if requested_file_result:
            result[FileStoreProp.RESULT] = \
                self._complete_file(file_entry, requested_file_result,
                                    segment, file_size, file_hash)
        else:
            self._write_file_segment(file_entry, segment)

        result[FileStoreProp.SEGMENTS_RECEIVED] = \
            file_entry[FileStoreProp.SEGMENTS_RECEIVED]

        return result

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param dxlclient.message.Request request: The request message
        """
        # Handle request
        logger.debug("Request received on topic: '%s'",
                     request.destination_topic)

        try:
            # Extract parameters from the request. Parameters all appear in the
            # 'other_fields' element in the request. The request payload, if
            # set, represents a segment of a file to be stored.
            params = request.other_fields

            file_id = params.get(FileStoreProp.ID)

            file_name = params.get(FileStoreProp.NAME)
            if not file_name:
                raise ValueError("File name was not specified")

            file_size = _get_value_as_int(params, FileStoreProp.SIZE)
            file_hash = params.get(FileStoreProp.HASH_SHA256)
            requested_file_result = self._get_requested_file_result(
                params, file_id, file_size, file_hash)

            segment_number = _get_value_as_int(
                params, FileStoreProp.SEGMENT_NUMBER)

            # Obtain or create a file entry for the file associated with the
            # request
            file_entry = self._get_file_entry(file_id, file_name)

            # Create response
            res = Response(request)

            # Store the next segment. If a requested_file_result is set,
            # validate that the result can be achieved -- that the file can
            # be stored correctly or that the store request can be properly
            # canceled.
            result = self._process_store_request(
                file_entry, request.payload, segment_number,
                requested_file_result, file_size, file_hash)

            # Set payload
            MessageUtils.dict_to_json_payload(res, result)

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)
