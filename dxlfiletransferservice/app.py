from __future__ import absolute_import
import logging

from dxlbootstrap.app import Application
from dxlclient.service import ServiceRegistrationInfo
from .requesthandlers import FileStoreRequestCallback

# Configure local logger
logger = logging.getLogger(__name__)


class FileTransferService(Application):
    """
    The "File Transfer DXL Python service" application class.
    """

    #: The DXL service type for the File Transfer service
    _SERVICE_TYPE = "/opendxl-file-transfer/service/file-transfer"

    #: The name of the "General" section within the application configuration
    #: file
    _GENERAL_CONFIG_SECTION = "General"

    #: The property used to specify the root directory under which files
    #: are stored
    _GENERAL_STORAGE_DIR_PROP = "storageDir"

    #: The property used to specify the root directory under which working
    #: files are stored
    _GENERAL_WORKING_DIR_PROP = "workingDir"

    #: The property used to specify a custom name for the store topic
    #: registered with the DXL fabric.
    _GENERAL_STORE_TOPIC_PROP = "storeTopic"

    #: The default subtopic to register with the DXL fabric if the store topic
    #: is not overridden in the configuration file
    _DEFAULT_STORE_SUBTOPIC = "file/store"

    def __init__(self, config_dir):
        """
        Constructor parameters:

        :param str config_dir: The location of the configuration files for the
            application
        """
        super(FileTransferService, self).__init__(
            config_dir, "dxlfiletransferservice.config")
        self._storage_dir = None
        self._working_dir = None
        self._store_topic = "{}/{}".format(self._SERVICE_TYPE,
                                           self._DEFAULT_STORE_SUBTOPIC)

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
        The application configuration (as read from the
        "dxlfiletransferservice.config" file)
        """
        return self._config

    def on_run(self):
        """
        Invoked when the application has started running.
        """
        logger.info("On 'run' callback.")

    def _get_setting_from_config(self, config, setting,
                                 default_value=None,
                                 raise_exception_if_missing=False):
        """
        Get the value for a setting in the application configuration file.

        :param RawConfigParser config: Config parser to get setting from.
        :param str setting: Name of the setting.
        :param default_value: Value to return if the setting is not found in
            the configuration file and `raise_exception_is_missing` is set
            to False.
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
            return_value = default_value

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
        self._working_dir = self._get_setting_from_config(
            config, self._GENERAL_WORKING_DIR_PROP)
        self._store_topic = self._get_setting_from_config(
            config, self._GENERAL_STORE_TOPIC_PROP,
            default_value=self._store_topic)

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

        logger.info("Registering request callback: %s. Topic: %s.",
                    "file_transfer_service_file_store",
                    self._store_topic)
        self.add_request_callback(
            service, self._store_topic,
            FileStoreRequestCallback(self.client,
                                     self._storage_dir,
                                     self._working_dir),
            False)

        self.register_service(service)
