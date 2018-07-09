Basic Store Example
===================

This sample sends a file to the DXL fabric for storage. The progress and result
of the file storage operation are displayed to the console.

This sample shows the specific DXL ``request messages`` which can be used to
send the file contents in multiple segments. This example primarily exists to
document the request message format. Storing files in this manner, however, is
not generally recommended for client applications. It is recommended instead to
use the `FileTransferClient` wrapper provided by
`File Transfer Python client library <https://github.com/opendxl-community/opendxl-file-transfer-client-python>`_
for sending files. This wrapper includes a much simpler API which abstracts
away the work needed to split the file into separate messages.

For the much simpler, recommended approach, see the documentation for the
`Basic Send File Request <https://opendxl-community.github.io/opendxl-file-transfer-client-python/pydoc/basicsendfilerequestexample.html>`_
example.

Prerequisites
*************

* The samples configuration step has been completed (see :doc:`sampleconfig`)
* The File Transfer DXL service is running (see :doc:`running`)

Running
*******

To run this sample execute the ``sample/basic/basic_store_example.py`` script
with the path to the file to be sent to the service as a parameter. For example,
to send a file named ``C:\test.exe`` to the service, you could run the sample
as follows:

    .. parsed-literal::

        python sample/basic/basic_store_example.py C:\\test.exe

As the file is being sent, a "Percent complete" indicator -- moving from 0% to
100% -- should be updated:

    .. code-block:: shell

        Percent complete: 5%

After the file has been uploaded completely, the response from the service and
some summary information for the file store operation should be printed out. For
example:

    .. code-block:: shell

        Percent complete: 100%
        Response to the request for the last segment:
        {
            "file_id": "7b89f71d-f348-45ee-aef3-4ac2555e92f8",
            "result": "store",
            "segments_received": 1750
        }
        Elapsed time (ms): 89546.39649391174

The service stores files under the directory configured for the `storageDir`
setting in the service configuration file. For example, if this setting were
specified as ``C:\\dxl-file-store`` and the base name of the file supplied as a
parameter to the ``basic_service_example.py`` script were ``test.exe``, the
file would be stored at the following location:

    .. parsed-literal::

        C:\\dxl-file-store\\test.exe

If a second parameter is passed to the example when run, the extra parameter
is used as the name of the subdirectory under which the file should be stored.
For example, the following command could be run:

    .. parsed-literal::

        python sample/basic/basic_store_example.py C:\\test.exe storesub1/storesub2

Assuming the storage directory setting on the server were specified as
``C:\\dxl-file-store``, the file would be stored at the following location:

    .. parsed-literal::

        C:\\dxl-file-store\\storesub1\\storesub2\\test.exe

Details
*******

The majority of the sample code is shown below:

    .. code-block:: python

        # Create the client
        with DxlClient(config) as client:
            # Connect to the fabric
            client.connect()

            logger.info("Connected to DXL fabric.")

            start = time.time()
            request_topic = "/opendxl-file-transfer/service/file-transfer/file/store"
            res_dict = {}

            # Open the local file to be sent to the service
            with open(STORE_FILE_NAME, 'rb') as file_handle:
                file_size = os.path.getsize(STORE_FILE_NAME)

                # Determine the number of segments that the file will be sent in. This
                # is only used for updating a progress counter on the command line
                # later.
                total_segments = file_size // MAX_SEGMENT_SIZE
                if file_size % MAX_SEGMENT_SIZE:
                    total_segments += 1
                file_hash = hashlib.sha256()

                segment_number = 0
                file_id = None
                bytes_read = 0
                continue_reading = True

                # Loop until all file segments have been sent to the service (or an
                # error has occurred).
                while continue_reading:
                    segment = file_handle.read(MAX_SEGMENT_SIZE)
                    segment_number += 1

                    # Create a request to be sent to the service. One request is
                    # sent for each file segment.
                    req = Request(request_topic)

                    # Request parameters are sent in the request 'other_fields'.
                    # The segment number is sent in every request.
                    other_fields = {
                        FileStoreProp.SEGMENT_NUMBER: str(segment_number)
                    }

                    # The 'file_id' is sent back from the service in the response
                    # for the first file segment. The 'file_id' must be included in
                    # each subsequent file segment request.
                    if file_id:
                        other_fields[FileStoreProp.ID] = file_id

                    # Update the running file hash for the bytes in the current
                    # segment
                    file_hash.update(segment)

                    # If all of the bytes in the local file have been read, this must
                    # be the last segment. Send a 'store' result, file 'name', and
                    # 'size' and sha256 'hash' values that the service can use to
                    # confirm that the full contents of the file were transmitted
                    # properly.
                    bytes_read += len(segment)
                    if bytes_read == file_size:
                        other_fields[FileStoreProp.NAME] = os.path.join(
                            STORE_FILE_DIR, os.path.basename(STORE_FILE_NAME))
                        other_fields[FileStoreProp.RESULT] = FileStoreResultProp.STORE
                        other_fields[FileStoreProp.SIZE] = str(file_size)
                        other_fields[FileStoreProp.HASH_SHA256] = file_hash.hexdigest()

                    # Set the full request parameters
                    req.other_fields = other_fields
                    req.payload = segment

                    # Send the file segment request to the DXL fabric. Exit if an
                    # error response is received.
                    res = client.sync_request(req, timeout=30)
                    if res.message_type == Message.MESSAGE_TYPE_ERROR:
                        print("\nError invoking service with topic '{}': {} ({})".format(
                            request_topic, res.error_message, res.error_code))
                        exit(1)

                    # Update the current percent complete on the console.
                    sys.stdout.write("\rPercent complete: {}%".format(
                        int((segment_number / total_segments) * 100)
                        if total_segments else 100))
                    sys.stdout.flush()

                    # Decode and display the response to the DXL request.
                    res_dict = MessageUtils.json_payload_to_dict(res)
                    if bytes_read < file_size:
                        logger.debug("Response to the request for segment '%s': \n%s",
                                     segment_number,
                                     MessageUtils.dict_to_json(res_dict,
                                                               pretty_print=True))
                    else:
                        continue_reading = False

                    # Retain the 'file_id' sent from the server so that it can be
                    # included in subsequent segment requests sent to the server.
                    if not file_id:
                        file_id = res_dict[FileStoreProp.ID]

            # Display the response from the service for the final segment request
            print("\nResponse to the request for the last segment: \n{}".
                  format(MessageUtils.dict_to_json(res_dict, pretty_print=True)))
            print("Elapsed time (ms): {}".format((time.time() - start) * 1000))


After connecting to the DXL fabric, the file name supplied as a parameter
to the example is opened.

The sample reads the contents of the file in segments of a size, in number of
bytes, controlled by the `MAX_SEGMENT_SIZE` constant. For each segment, a
``request message`` is sent to the file store topic registered by the File
Transfer service, ``/opendxl-file-transfer/service/file-transfer/file/store``. A
SHA-256 hash is updated for each of the bytes read from the file.

The ``payload`` for each request message contains the content of the next
segment in the file. The parameters which describe the file segment are
specified as a ``dict`` in the ``other_fields`` property in the message.

For the first file segment, the ``other_fields`` dict includes the following
key/value pairs:

    +---------------------------------+----------------------------------------------------+
    | Key                             | Value                                              |
    +=================================+====================================================+
    | `FileStoreProp.SEGMENT_NUMBER`  | 1 (first segment)                                  |
    +---------------------------------+----------------------------------------------------+

In the response received for the request for the first segment, the server
provides a ``file_id``. The ``file_id`` is included in the request message
for each subsequent segment.

For each of the segments prior to the last one for the file, the
``other_fields`` dict includes the following:

    +---------------------------------+----------------------------------------------------+
    | Key                             | Value                                              |
    +=================================+====================================================+
    | `FileStoreProp.ID`              | The ``file_id`` returned in the response to the    |
    |                                 | first segment request.                             |
    +---------------------------------+----------------------------------------------------+
    | `FileStoreProp.SEGMENT_NUMBER`  | The next segment number (2, 3, ...)                |
    +---------------------------------+----------------------------------------------------+

For the final segment request, the ``other_fields`` dict includes the following:

    +---------------------------------+----------------------------------------------------+
    | Key                             | Value                                              |
    +=================================+====================================================+
    | `FileStoreProp.ID`              | The ``file_id`` returned in the response to the    |
    |                                 | first segment request.                             |
    +---------------------------------+----------------------------------------------------+
    | `FileStoreProp.SEGMENT_NUMBER`  | The last segment number                            |
    +---------------------------------+----------------------------------------------------+
    | `FileStoreProp.RESULT`          | `FileStoreResultProp.STORE`, a value which         |
    |                                 | indicates that the fully transfered file should be |
    |                                 | "stored".                                          |
    +---------------------------------+----------------------------------------------------+
    | `FileStoreProp.NAME`            | Name of the file to be stored on the server.       |
    |                                 | For the example above, this would be set to        |
    |                                 | ``test.exe``.                                      |
    +---------------------------------+----------------------------------------------------+
    | `FileStoreProp.SIZE`            | The expected size (in bytes) of the complete file. |
    +---------------------------------+----------------------------------------------------+
    | `FileStoreProp.HASH_SHA256`     | The expected SHA-256 computed from the bytes of the|
    |                                 | complete file.                                     |
    +---------------------------------+----------------------------------------------------+

The service uses the `FileStoreProp.SIZE` and `FileStoreProp.HASH_SHA256`
values to verify that it has received the proper contents for the file. If this
verification fails, the service sends an `ErrorResponse` for this request.

If either the `SIZE` or `HASH_SHA256` verification fails or if the final segment
request sent by the client provides a value of `FileStoreResultProp.CANCEL` for
the `FileStoreProp.RESULT` key, any resources which had been utilized by the
service for storing the file (including any partially-stored file contents)
would be purged. The client may choose to send the `FileStoreResultProp.CANCEL`
result, for example, due to an error for which the client intends to terminate
the file transfer.

Assuming the file store operation is successful, the last response from the
service is printed to the console output. The response contains a ``sha256``
hash and ``size`` of the file bytes which were stored on the server.
