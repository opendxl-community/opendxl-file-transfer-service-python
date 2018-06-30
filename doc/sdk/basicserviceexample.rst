Basic Service Example
=====================

This sample registers a file store request callback with DXL as part of a custom
service. The sample uses a client application wrapper to send a file via the
DXL fabric to the request callback for storage. The progress and result of the
file storage operation are displayed to the console.

Prerequisites
*************

* The samples configuration step has been completed (see :doc:`sampleconfig`)

Setup
*****

Modify the example to include the storage directory under which the service
should store files sent to it.

For example:

    .. code-block:: python

        STORE_DIR = "C:\\dxl-file-store"

Note that the service would need to have write permissions to the directory
which is provided. If the directory does not exist when the service first starts
up, the service attempts to create the directory, including any intermediate
subdirectories in the path which may not yet exist.

Running
*******

To run this sample execute the ``sample/basic/basic_service_example.py`` script
with the path to the file to be sent to the service as a parameter. For example,
to send a file named ``C:\test.exe`` to the service, you could run the sample
as follows:

    .. parsed-literal::

        python sample/basic/basic_service_example.py C:\\test.exe

As the file is being sent, a "Percent complete" indicator -- moving from 0% to
100% -- should be updated:

    .. code-block:: shell

        Percent complete: 5%

After the file has been uploaded completely, the response from the service and
some summary information for the file store operation should be printed out. For
example:

    .. code-block:: shell

        Percent complete: 100%
        Response:
        {
            "file_id": "7b89f71d-f348-45ee-aef3-4ac2555e92f8",
            "hashes": {
                "sha256": "a2e52129a28feec1ee3f22f5aaf9bdecbb02d51af6da408ace0a2ac2e0365c8b"
            },
            "size": 89579672
        }
        Elapsed time (ms): 89546.39649391174

The service stores files in a subdirectory under the storage directory named
``files``. For example, if the `STORE_DIR` constant in the example were set to
``C:\\dxl-file-store`` and the base name of the file supplied as a parameter to
the ``basic_service_example.py`` script were ``test.exe``, the file would be
stored at the following location:

    .. parsed-literal::

        C:\\dxl-file-store\\files\\test.exe

Details
*******

The majority of the sample code is shown below:

    .. code-block:: python

        # The topic for the service to respond to
        SERVICE_TOPIC = "/file-transfer-sample/basic-service"

        ...

        # Create the client
        with DxlClient(config) as dxl_client:

            # Connect to the fabric
            dxl_client.connect()

            logger.info("Connected to DXL fabric.")

            # Create service registration object
            info = ServiceRegistrationInfo(dxl_client, "myService")

            # Add a topic for the service to respond to
            info.add_topic(SERVICE_TOPIC,
                           FileStoreRequestCallback(dxl_client, STORE_DIR))

            # Register the service with the fabric (wait up to 10 seconds for
            # registration to complete)
            dxl_client.register_service_sync(info, 10)

            # Create client wrapper
            file_transfer_client = FileTransferClient(dxl_client, SERVICE_TOPIC)

            start = time.time()

            # Invoke the send file request method to store the file on the server
            resp = file_transfer_client.send_file_request(
                STORE_FILE_NAME, max_segment_size=MAX_SEGMENT_SIZE,
                callback=update_progress)

            # Print out the response (convert dictionary to JSON for pretty printing)
            print("\nResponse:\n{}".format(
                MessageUtils.dict_to_json(resp.to_dict(), pretty_print=True)))

            print("Elapsed time (ms): {}".format((time.time() - start) * 1000))


The value for the `SERVICE_TOPIC` constant is used as a topic name on the DXL
fabric, both for registering a ``request callback`` and for file storage
requests made from a client.

After connecting to the DXL fabric, a service is registered. The service
registration associates an instance of the
:class:`dxlfiletransferservice.requesthandlers.FileStoreRequestCallback` class
with the `SERVICE_TOPIC`. The root directory under which the request callback
should store files is supplied to the callback, the `STORE_DIR` constant.

The next step is to create a `FileTransferClient`, including the `SERVICE_TOPIC`
constant as the name of the topic to use when sending to the DXL fabric the
segments of the file to store.

The final step is to invoke the `send_file_request` method on the
`FileTransferClient` instance. This call sends the file contents to the DXL
fabric. As the `FileStoreRequestCallback` request handler (registered with the
DXL fabric above) receives DXL ``request messages`` with the file segments, the
segments are reassembled into a single file which is stored to the file system.

Assuming the file store operation is successful, the last response from the
service is printed to the console output. The response contains a ``sha256``
hash and ``size`` of the file bytes which were stored on the server.
