from __future__ import absolute_import
import hashlib
import logging
import os
import threading
import uuid

from dxlclient.callbacks import RequestCallback
from dxlclient.message import Request, Response, ErrorResponse  # pylint: disable=unused-import
from dxlbootstrap.util import MessageUtils
from .constants import FileUpload

# Configure local logger
logger = logging.getLogger(__name__)


def _get_value_as_int(value, key):
    return_value = value
    try:
        return_value = int(return_value)
    except ValueError:
        raise ValueError(
            "'{}' of '{}' could not be converted to an int".format(
                key, return_value))
    return return_value


def _get_value_as_bool(value, key):
    return_value = value
    if not isinstance(return_value, bool):
        return_value = str(return_value).strip().lower()
        if return_value in ("true", "yes", "1"):
            return_value = True
        elif return_value in ("false", "no", "0"):
            return_value = False
        else:
            raise ValueError(
                "'{}' of '{}' could not be converted to an bool".format(
                    key, return_value))
    return return_value


def _get_value_from_dict(dict_obj, key, default_value=None,
                         return_type=str, raise_exception_if_missing=True):
    return_value = default_value
    if isinstance(dict_obj, dict):
        return_value = dict_obj.get(key)
        if return_value is None:
            if raise_exception_if_missing:
                raise ValueError("Required key '{}' has no value".format(key))
            else:
                return_value = default_value
        else:
            if return_type == int:
                return_value = _get_value_as_int(return_value, key)
            elif return_type == bool:
                return_value = _get_value_as_bool(return_value, key)
            else:
                return_value = str(return_value).strip()
    elif raise_exception_if_missing:
        raise ValueError(
            "Dictionary not provided to get key '{}' from".format(key))
    return return_value


class FileUploadManager(object):
    _FILE_ENTRY_SEGMENTS_RECEIVED = "segments_received"
    _FILE_ENTRY_SEGMENTS = "segments"

    def __init__(self, base_dir):
        self._lock = threading.Lock()
        self._files = {}
        self._base_dir = base_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        logger.info("Using file store at '%s'", os.path.abspath(base_dir))

    def create_file_entry(self, name, size, segment_count):
        file_id = str(uuid.uuid4()).lower()
        logger.info(
            "Creating file entry for id '%s': name='%s', size='%d', segments='%d'",
            file_id, name, size, segment_count
        )
        file_entry = {
            FileUpload.FILE_NAME: name,
            FileUpload.FILE_SIZE: size,
            FileUpload.FILE_TOTAL_SEGMENTS: segment_count,
            self._FILE_ENTRY_SEGMENTS_RECEIVED: 0,
            self._FILE_ENTRY_SEGMENTS: [None] * segment_count
        }
        with self._lock:
            self._files[file_id] = file_entry
        return file_id

    def upload_file_segment(self, file_id, segment_number, data):
        return_val = {}
        logger.debug("Uploading segment '%d' for file id '%s'", segment_number,
                     file_id)
        with self._lock:
            file_entry = self._files.get(file_id)
            if file_entry:
                total_segments = file_entry[FileUpload.FILE_TOTAL_SEGMENTS]
                if (segment_number < 1) or (segment_number > total_segments):
                    raise IndexError(
                        "Invalid segment number for file id '" + file_id +
                        "'. Segment number: '" + str(segment_number) +
                        "'. Max segment number: '" + str(total_segments) +
                        "'.")
                else:
                    segments = file_entry[self._FILE_ENTRY_SEGMENTS]
                    if not segments[segment_number - 1]:
                        file_entry[self._FILE_ENTRY_SEGMENTS_RECEIVED] += 1
                    segments[segment_number - 1] = data
                return_val = {
                    FileUpload.FILE_SEGMENT_RECEIVED: segment_number,
                    FileUpload.FILE_SEGMENTS_REMAINING:
                        total_segments - file_entry[
                            self._FILE_ENTRY_SEGMENTS_RECEIVED],
                }
            else:
                raise KeyError(
                    "Could not upload segment for unknown file id '{}'".format(
                        file_id
                    ))
        return return_val

    def cancel_file(self, file_id):
        logger.debug("Canceling storage of file for id '%s'", file_id)
        with self._lock:
            if file_id in self._files:
                del self._files[file_id]
                logger.info("Canceled storage of file for id '%s'", file_id)
            else:
                logger.info(
                    "Unable to cancel storage of file for unknown id: %s",
                    file_id
                )

    def store_file(self, file_id, file_hash):
        logger.debug("Storing file entry '%s': hash='%s'", file_id, file_hash)
        with self._lock:
            file_entry = self._files.get(file_id)
            if file_entry:
                segments_remaining = \
                    file_entry[FileUpload.FILE_TOTAL_SEGMENTS] - \
                    file_entry[self._FILE_ENTRY_SEGMENTS_RECEIVED]
                if segments_remaining:
                    raise IOError(
                        "Cannot store incomplete file for id '" +
                        file_id + "'. Segments remaining: '" +
                        str(segments_remaining) + "'."
                    )
                del self._files[file_id]
            else:
                raise KeyError(
                    "Could not store file for unknown file id '{}'".format(
                        file_id
                    ))
        segments = file_entry[self._FILE_ENTRY_SEGMENTS]

        received_file_size = 0
        received_file_hash = hashlib.md5()
        for segment in segments:
            received_file_size += len(segment)
            received_file_hash.update(segment)
        received_file_hash = received_file_hash.hexdigest()

        expected_file_size = file_entry[FileUpload.FILE_SIZE]
        if expected_file_size != received_file_size:
            raise IOError(
                "Unexpected file size for id '" + file_id +
                "'. Expected: '" + str(expected_file_size) +
                "'. Received: '" + str(received_file_size) + "'")

        if file_hash != received_file_hash:
            raise IOError(
                "Unexpected file hash for id '" + file_id +
                "'. Expected: '" + file_hash +
                "'. Received: '" + received_file_hash + "'")

        file_dir = os.path.join(self._base_dir, file_id)
        file_name = os.path.join(file_dir,
                                 file_entry[FileUpload.FILE_NAME])
        try:
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            with open(file_name, "wb") as file_handle:
                for segment in segments:
                    file_handle.write(segment)
            logger.info("Stored file '%s' for id '%s'", file_name, file_id)
        except Exception as ex:
            logger.exception("Failed to store file '%s' for id '%s'",
                             file_name, file_id)
            raise Exception(
                "Failed to store file for file id '{}': {}".format(
                    file_id, str(ex))
            )


class FileUploadCreateRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_create' request handler registered with topic
    '/opendxl-file-transfer/service/file/create'
    """

    def __init__(self, app, upload_manager):
        """
        Constructor parameters:

        :param app: The application this handler is associated with
        :param FileUploadManager upload_manager: The upload manager instance
            to use for storing files.
        """
        super(FileUploadCreateRequestCallback, self).__init__()
        self._app = app
        self._upload_manager = upload_manager

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param Request request: The request message
        """
        # Handle request
        logger.debug("Request received on topic: '%s'",
                     request.destination_topic)

        try:
            request_dict = MessageUtils.json_payload_to_dict(request)

            file_id = self._upload_manager.create_file_entry(
                _get_value_from_dict(request_dict, FileUpload.FILE_NAME),
                _get_value_from_dict(request_dict, FileUpload.FILE_SIZE,
                                     return_type=int),
                _get_value_from_dict(request_dict,
                                     FileUpload.FILE_TOTAL_SEGMENTS,
                                     return_type=int)
            )

            # Create response
            res = Response(request)

            # Set payload
            MessageUtils.dict_to_json_payload(
                res, {FileUpload.FILE_ID: file_id})

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)


class FileUploadSegmentRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_upload' request handler registered with topic
    '/opendxl-file-transfer/service/file/upload'
    """

    def __init__(self, app, upload_manager):
        """
        Constructor parameters:

        :param app: The application this handler is associated with
        :param FileUploadManager upload_manager: The upload manager instance
            to use for storing files.
        """
        super(FileUploadSegmentRequestCallback, self).__init__()
        self._app = app
        self._upload_manager = upload_manager

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param Request request: The request message
        """
        # Handle request
        logger.debug("Request received on topic: '%s'",
                     request.destination_topic)

        try:
            file_id = _get_value_from_dict(request.other_fields,
                                           FileUpload.FILE_ID)
            segment_number = _get_value_from_dict(
                request.other_fields, FileUpload.FILE_SEGMENT_NUMBER,
                return_type=int
            )

            payload = request.payload
            if not payload:
                raise ValueError(
                    "No payload provided for segment '" + str(segment_number) +
                    "' for file id '" + str(file_id) + "'")

            upload_result = self._upload_manager.upload_file_segment(
                file_id, segment_number, payload)

            # Create response
            res = Response(request)

            # Set payload
            MessageUtils.dict_to_json_payload(res, upload_result)

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)


class FileUploadCompleteRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_create' request handler registered with topic
    '/opendxl-file-transfer/service/file/create'
    """

    def __init__(self, app, upload_manager):
        """
        Constructor parameters:

        :param app: The application this handler is associated with
        :param FileUploadManager upload_manager: The upload manager instance
            to use for storing files.
        """
        super(FileUploadCompleteRequestCallback, self).__init__()
        self._app = app
        self._upload_manager = upload_manager

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param Request request: The request message
        """
        # Handle request
        logger.debug("Request received on topic: '%s'",
                     request.destination_topic)

        try:
            request_dict = MessageUtils.json_payload_to_dict(request)

            file_id = _get_value_from_dict(request_dict, FileUpload.FILE_ID)

            if _get_value_from_dict(request_dict,
                                    FileUpload.FILE_CANCEL,
                                    default_value=False,
                                    return_type=bool,
                                    raise_exception_if_missing=False):
                self._upload_manager.cancel_file(file_id)
            else:
                self._upload_manager.store_file(
                    file_id, _get_value_from_dict(request_dict,
                                                  FileUpload.FILE_HASH))

            # Create response
            res = Response(request)

            # Set payload
            MessageUtils.dict_to_json_payload(res, {})

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)
