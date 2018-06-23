from __future__ import absolute_import
from collections import OrderedDict
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

    _SERVICE_TYPE = "/opendxl-file-transfer/service/file-transfer"

    _GENERAL_CONFIG_SECTION = "General"

    _GENERAL_STORAGE_DIR_PROP = "storageDir"
    _GENERAL_SERVICE_UNIQUE_ID_PROP = "serviceUniqueId"

    def __init__(self, config_dir):
        """
        Constructor parameters:

        :param config_dir: The location of the configuration files for the
            application
        """
        super(FileTransferService, self).__init__(
            config_dir, "dxlfiletransferservice.config")
        self._service_unique_id = None
        self._storage_dir = None

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

    def _get_setting_from_config(self, config, setting,
                                 raise_exception_if_missing=False):
        """
        Get the value for a setting in the application configuration file.

        :param RawConfigParser config: Config parser to get setting from.
        :param str setting: Name of the setting.
        :param bool raise_exception_if_missing: Whether or not to raise an
            exception if the setting is missing from the configuration file.
        :return: Value for the setting.
        :raises ValueError: If the setting cannot be found in the configuration
            file and 'raise_exception_if_missing' is set to 'True'.
        """
        section = self._GENERAL_CONFIG_SECTION
        if config.has_option(section, setting):
            try:
                return_value = config.get(section, setting)
            except ValueError as ex:
                raise ValueError(
                    "Unexpected value for setting {} in section {}: {}".format(
                        setting, section, ex))
            return_value = return_value.strip()
            if len(return_value) is 0 and raise_exception_if_missing:
                raise ValueError(
                    "Required setting {} in section {} is empty".format(
                        setting, section))
        elif raise_exception_if_missing:
            raise ValueError(
                "Required setting {} not found in {} section".format(
                    setting, section))
        else:
            return_value = None

        return return_value

    def on_load_configuration(self, config):
        """
        Invoked after the application-specific configuration has been loaded

        This callback provides the opportunity for the application to parse
        additional configuration properties.

        :param config: The application configuration
        """
        logger.info("On 'load configuration' callback.")

        self._storage_dir = self._get_setting_from_config(
            config, self._GENERAL_STORAGE_DIR_PROP,
            raise_exception_if_missing=True)

        self._service_unique_id = self._get_setting_from_config(
            config, self._GENERAL_SERVICE_UNIQUE_ID_PROP)


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

        logger.info("Registering service: file_transfer_service")
        service = ServiceRegistrationInfo(self._dxl_client,
                                          self._SERVICE_TYPE)

        file_store_topic = "{}{}/file/store".format(
            self._SERVICE_TYPE,
            "/{}".format(self._service_unique_id)
            if self._service_unique_id else "")

        logger.info("Registering request callback: %s. Topic: %s.",
                    "file_transfer_service_file_store",
                    file_store_topic)
        self.add_request_callback(
            service, file_store_topic,
            FileStoreRequestCallback(self, self._storage_dir),
            False)

        self.register_service(service)
