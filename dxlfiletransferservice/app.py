from __future__ import absolute_import
import logging

from dxlbootstrap.app import Application
from dxlclient.service import ServiceRegistrationInfo
from .requesthandlers import *

# Configure local logger
logger = logging.getLogger(__name__)


class FileTransferService(Application):
    """
    The "File Transfer DXL Python service" application class.
    """

    def __init__(self, config_dir):
        """
        Constructor parameters:

        :param config_dir: The location of the configuration files for the
            application
        """
        super(FileTransferService, self).__init__(config_dir,
                                                  "dxlfiletransferservice.config")

    @property
    def client(self):
        """
        The DXL client used by the application to communicate with the DXL
        fabric
        """
        return self._dxl_client

    @property
    def config(self):
        """
        The application configuration (as read from the "dxlfiletransferservice.config" file)
        """
        return self._config

    def on_run(self):
        """
        Invoked when the application has started running.
        """
        logger.info("On 'run' callback.")

    def on_load_configuration(self, config):
        """
        Invoked after the application-specific configuration has been loaded

        This callback provides the opportunity for the application to parse
        additional configuration properties.

        :param config: The application configuration
        """
        logger.info("On 'load configuration' callback.")

    def on_dxl_connect(self):
        """
        Invoked after the client associated with the application has connected
        to the DXL fabric.
        """
        logger.info("On 'DXL connect' callback.")

    def on_register_services(self):
        """
        Invoked when services should be registered with the application
        """
        # Register service 'file_transfer_service'
        logger.info("Registering service: %s", "file_transfer_service")
        service = ServiceRegistrationInfo(self._dxl_client,
                                          "/opendxl-file-transfer/service")
        logger.info("Registering request callback: %s",
                    "file_transfer_service_file_create")
        self.add_request_callback(service,
                                  "/opendxl-file-transfer/service/file/create",
                                  FileCreateRequestCallback(self), True)
        logger.info("Registering request callback: %s",
                    "file_transfer_service_file_upload")
        self.add_request_callback(service,
                                  "/opendxl-file-transfer/service/file/upload",
                                  FileUploadRequestCallback(self), True)
        self.register_service(service)
