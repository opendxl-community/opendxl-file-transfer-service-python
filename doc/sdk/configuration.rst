Configuration
=============

The File Transfer DXL Python service application requires a set of configuration
files to operate.

This distribution contains a ``config`` sub-directory that includes the
configuration files that must be populated prior to running the application.

Each of these files are documented throughout the remainder of this page.

Application configuration directory:

    .. code-block:: python

        config/
            dxlclient.config
            dxlfiletransferservice.config
            logging.config (optional)

.. _dxl_client_config_file_label:

DXL Client Configuration File (dxlclient.config)
------------------------------------------------

    The required ``dxlclient.config`` file is used to configure the DXL client
    that will connect to the DXL fabric.

    The steps to populate this configuration file are the same as those
    documented in the `OpenDXL Python SDK`, see the
    `OpenDXL Python SDK Samples Configuration <https://opendxl.github.io/opendxl-client-python/pydoc/sampleconfig.html>`_
    page for more information.

    The following is an example of a populated DXL client configuration file:

        .. code-block:: python

            [Certs]
            BrokerCertChain=c:\\certificates\\brokercerts.crt
            CertFile=c:\\certificates\\client.crt
            PrivateKey=c:\\certificates\\client.key

            [Brokers]
            {5d73b77f-8c4b-4ae0-b437-febd12facfd4}={5d73b77f-8c4b-4ae0-b437-febd12facfd4};8883;mybroker.mcafee.com;192.168.1.12
            {24397e4d-645f-4f2f-974f-f98c55bdddf7}={24397e4d-645f-4f2f-974f-f98c55bdddf7};8883;mybroker2.mcafee.com;192.168.1.13

.. _dxl_service_config_file_label:

File Transfer DXL Python Service (dxlfiletransferservice.config)
----------------------------------------------------------------

    The required ``dxlfiletransferservice.config`` file is used to configure the application.

    The following is an example of a populated application configuration file:

        .. code-block:: python

            [General]
            # Directory under which to store files (required, no default)
            storageDir=

            # Name of the topic to register with the DXL fabric for the file store
            # request handler. (optional, defaults to
            # "/opendxl-file-transfer/service/file-transfer/file/store")
            ;storeTopic=/opendxl-file-transfer/service/file-transfer/file/store

            # Working directory under which files (or segments of files) may be stored in
            # the process of being transferred to the 'storageDir' (optional, defaults to
            # "<storageDir>/.workdir")
            ;workingDir=<storageDir>/.workdir

    **General**

        The ``General`` section is used to specify file storage settings.

        +------------------------+----------+-------------------------------------------------------------------------+
        | Name                   | Required | Description                                                             |
        +========================+==========+=========================================================================+
        | storageDir             | yes      | Directory under which to store files. The running service must have     |
        |                        |          | create directory and write permissions to the contents under this       |
        |                        |          | directory. If the directory does not exist at service startup, the      |
        |                        |          | will attempt to create it. If the directory cannot be created, the      |
        |                        |          | service will fail with an error at startup.                             |
        |                        |          |                                                                         |
        |                        |          | For example, if the ``storageDir`` were specified as                    |
        |                        |          | ``/root/dxl-file-store`` and the name specified for the file to be      |
        |                        |          | stored were ``/this/file/test.txt``, respectively, the file stored on   |
        |                        |          | the server would be:                                                    |
        |                        |          |                                                                         |
        |                        |          | ``/root/dxl-file-store/this/file/test.txt``                             |
        +------------------------+----------+-------------------------------------------------------------------------+
        | workingDir             | no       | Working directory under which files (or segments of files) may be stored|
        |                        |          | in the process of being transferred to the ``storageDir``. If not set,  |
        |                        |          | this defaults to a directory named ``.workdir`` under the directory     |
        |                        |          | specified for the ``storageDir`` setting.                               |
        +------------------------+----------+-------------------------------------------------------------------------+
        | storeTopic             | no       | Name of the topic to register with the DXL fabric for the file store    |
        |                        |          | request handler. If not set, the service registers a default topic of:  |
        |                        |          |                                                                         |
        |                        |          | ``/opendxl-file-transfer/service/file-transfer/file/store``             |
        +------------------------+----------+-------------------------------------------------------------------------+


Logging File (logging.config)
-----------------------------

    The optional ``logging.config`` file is used to configure how the
    application writes log messages.
