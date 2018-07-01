Running
=======

Once the application library has been installed and the configuration files are
populated it can be started by executing the following command line:

    .. parsed-literal::

        python -m dxlfiletransferservice <configuration-directory>

    The ``<configuration-directory>`` argument must point to a directory
    containing the configuration files required for the application (see
    :doc:`configuration`).

For example:

    .. parsed-literal::

        python -m dxlfiletransferservice config

Output
------

The output from starting the service should appear similar to the following:

    .. parsed-literal::

        Running application ...
        On 'run' callback.
        On 'load configuration' callback.
        Incoming message configuration: queueSize=1000, threadCount=10
        Message callback configuration: queueSize=1000, threadCount=10
        Attempting to connect to DXL fabric ...
        Connected to DXL fabric.
        Registering service: file_transfer_service
        Registering request callback: file_transfer_service_file_store. Topic: /opendxl-file-transfer/service/file-transfer/file/store.
        Using storage dir: /root/dxl-file-store
        On 'DXL connect' callback.
