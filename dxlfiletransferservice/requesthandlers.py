from __future__ import absolute_import
import logging

from dxlclient.callbacks import RequestCallback
from dxlclient.message import Response, ErrorResponse
from dxlbootstrap.util import MessageUtils
from .store import FileStoreManager

# Configure local logger
logger = logging.getLogger(__name__)


class FileStoreRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_store' request handler registered with topic
    '/opendxl-file-transfer/service/file/store'
    """

    def __init__(self, app, storage_dir):
        """
        Constructor parameters:

        :param dxlfiletransferservice.app.FileTransferService app: The
            application this handler is associated with
        :param str storage_dir: Directory under which files are stored
        """
        super(FileStoreRequestCallback, self).__init__()
        self._store_manager = FileStoreManager(storage_dir)
        self._app = app

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param dxlclient.message.Request request: The request message
        """
        # Handle request
        logger.debug("Request received on topic: '%s'",
                     request.destination_topic)

        try:
            # Create response
            res = Response(request)

            # Store the next segment.
            result = self._store_manager.store_segment(request)

            # Set payload
            MessageUtils.dict_to_json_payload(res, result.to_dict())

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)
