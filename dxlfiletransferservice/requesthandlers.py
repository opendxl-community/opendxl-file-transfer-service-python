from __future__ import absolute_import
import logging

from dxlclient.callbacks import RequestCallback
from dxlclient.message import Response, ErrorResponse
from dxlbootstrap.util import MessageUtils

# Configure local logger
logger = logging.getLogger(__name__)


class FileCreateRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_create' request handler registered with topic
    '/opendxl-file-transfer/service/file/create'
    """

    def __init__(self, app):
        """
        Constructor parameters:

        :param app: The application this handler is associated with
        """
        super(FileCreateRequestCallback, self).__init__()
        self._app = app

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param request: The request message
        """
        # Handle request
        logger.info("Request received on topic: '%s' with payload: '%s'",
                    request.destination_topic,
                    MessageUtils.decode_payload(request))

        try:
            # Create response
            res = Response(request)

            # Set payload
            MessageUtils.encode_payload(res,
                                        "file_transfer_service_file_create response payload")

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)


class FileUploadRequestCallback(RequestCallback):
    """
    'file_transfer_service_file_upload' request handler registered with topic
    '/opendxl-file-transfer/service/file/upload'
    """

    def __init__(self, app):
        """
        Constructor parameters:

        :param app: The application this handler is associated with
        """
        super(FileUploadRequestCallback, self).__init__()
        self._app = app

    def on_request(self, request):
        """
        Invoked when a request message is received.

        :param request: The request message
        """
        # Handle request
        logger.info("Request received on topic: '%s' with payload: '%s'",
                    request.destination_topic,
                    MessageUtils.decode_payload(request))

        try:
            # Create response
            res = Response(request)

            # Set payload
            MessageUtils.encode_payload(res,
                                        "file_transfer_service_file_upload response payload")

            # Send response
            self._app.client.send_response(res)

        except Exception as ex:
            logger.exception("Error handling request")
            err_res = ErrorResponse(request, error_code=0,
                                    error_message=MessageUtils.encode(str(ex)))
            self._app.client.send_response(err_res)
