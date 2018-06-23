from __future__ import absolute_import
import hashlib
import logging
import os
import shutil
import threading
import uuid

from dxlclient.callbacks import RequestCallback
from dxlclient.message import Request, Response, ErrorResponse  # pylint: disable=unused-import
from dxlbootstrap.util import MessageUtils
from .constants import FileStoreParam

# Configure local logger
logger = logging.getLogger(__name__)

def _get_value_as_int(dict_obj, key):
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

    _STORAGE_WORK_SUBDIR = ".workdir"
    _FILE_HASHER = "file_hasher"
    _FILE_DIR = "dir"
    _FILE_FULL_PATH = "full_path"

    def __init__(self, app, storage_dir):
        """
        Constructor parameters:

        :param app: The application this handler is associated with
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
        for incomplete_file_id in os.listdir(self._storage_work_dir):
            logger.info("Purging content for incomplete file id: '{}'".format(
                incomplete_file_id
            ))
            file_path = os.path.join(self._storage_dir, incomplete_file_id)
            if os.path.exists(file_path):
                shutil.rmtree(file_path)
            os.remove(os.path.join(self._storage_work_dir, incomplete_file_id))

    def _write_file_segment(self, file_entry, segment):
        segments_received = file_entry[FileStoreParam.FILE_SEGMENTS_RECEIVED]
        logger.debug("Storing segment '%d' for file id: '%s'",
                     segments_received, file_entry[FileStoreParam.FILE_ID])
        with open(file_entry[self._FILE_FULL_PATH], "ab+") as file_handle:
            if segment:
                file_handle.write(segment)
                file_entry[self._FILE_HASHER].update(segment)
        file_entry[FileStoreParam.FILE_SEGMENTS_RECEIVED] = segments_received

    @staticmethod
    def _get_requested_file_result(params, file_id, file_size, file_hash):
        requested_file_result = params.get(FileStoreParam.FILE_RESULT)
        if requested_file_result:
            if requested_file_result == FileStoreParam.FILE_RESULT_CANCEL:
                if not file_id:
                    raise ValueError("File id to cancel must be specified")
            elif requested_file_result == FileStoreParam.FILE_RESULT_STORE:
                if file_size is None:
                    raise ValueError(
                        "File size must be specified for store request")
                if file_size is not None and not file_hash:
                    raise ValueError(
                        "File hash must be specified for store request")
            else:
                raise ValueError(
                    "Unexpected '{}' value: '{}'".
                        format(FileStoreParam.FILE_RESULT,
                               requested_file_result))
        return requested_file_result

    def _get_file_entry(self, file_id, file_name):
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
                FileStoreParam.FILE_ID: file_id,
                FileStoreParam.FILE_NAME: file_name,
                FileStoreParam.FILE_SEGMENTS_RECEIVED: 0,
                self._FILE_HASHER: hashlib.md5(),
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
        file_id = file_entry[FileStoreParam.FILE_ID]
        file_dir = file_entry[self._FILE_DIR]
        full_file_path = file_entry[self._FILE_FULL_PATH]

        workdir_file = os.path.join(self._storage_work_dir, file_id)
        if os.path.exists(workdir_file):
            os.remove(workdir_file)

        if requested_file_result == FileStoreParam.FILE_RESULT_STORE:
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
            result = FileStoreParam.FILE_RESULT_STORE
        else:
            shutil.rmtree(file_dir)
            logger.info("Canceled storage of file for id '%s'", file_id)
            result = FileStoreParam.FILE_RESULT_CANCEL

        return result

    def _process_segment(self, file_entry, segment, segment_number,
                         requested_file_result, file_size, file_hash):
        result = {FileStoreParam.FILE_ID: file_entry[FileStoreParam.FILE_ID]}

        if requested_file_result != FileStoreParam.FILE_RESULT_CANCEL:
            segments_received = file_entry[
                FileStoreParam.FILE_SEGMENTS_RECEIVED]
            if (segments_received + 1) == segment_number:
                file_entry[FileStoreParam.FILE_SEGMENTS_RECEIVED] = \
                    segments_received + 1
            else:
                raise ValueError(
                    "Unexpected segment. Expected: '{}'. Received: '{}'".
                    format(segments_received + 1, segment_number))

        if requested_file_result:
            result[FileStoreParam.FILE_RESULT] = \
                self._complete_file(file_entry, requested_file_result,
                                    segment, file_size, file_hash)
        else:
            self._write_file_segment(file_entry, segment)

        result[FileStoreParam.FILE_SEGMENTS_RECEIVED] = \
            file_entry[FileStoreParam.FILE_SEGMENTS_RECEIVED]

        return result

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param Request request: The request message
        """
        # Handle request
        logger.debug("Request received on topic: '%s'",
                     request.destination_topic)

        try:
            params = request.other_fields

            file_id = params.get(FileStoreParam.FILE_ID)

            file_name = params.get(FileStoreParam.FILE_NAME)
            if not file_name:
                raise ValueError("File name was not specified")

            file_size = _get_value_as_int(params, FileStoreParam.FILE_SIZE)
            file_hash = params.get(FileStoreParam.FILE_HASH)
            requested_file_result = self._get_requested_file_result(
                params, file_id, file_size, file_hash)

            segment_number = _get_value_as_int(
                params, FileStoreParam.FILE_SEGMENT_NUMBER)

            file_entry = self._get_file_entry(file_id, file_name)

            # Create response
            res = Response(request)

            result = self._process_segment(
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
