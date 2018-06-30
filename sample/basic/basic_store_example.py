from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import hashlib
import os
import sys
import time

from dxlclient.client_config import DxlClientConfig
from dxlclient.client import DxlClient
from dxlclient.message import Message, Request
from dxlbootstrap.util import MessageUtils
from dxlfiletransferclient import FileStoreProp, FileStoreResultProp

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

# Extract the name of the file to upload from a command line argument
STORE_FILE_NAME = None
if len(sys.argv) == 2:
    STORE_FILE_NAME = sys.argv[1]
else:
    print("Name of file to store must be specified as an argument")
    exit(1)

# Send the file contents in 50 KB segments. The default maximum size
# for a DXL broker message is 1 MB.
MAX_SEGMENT_SIZE = 50 * (2 ** 10)

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
                other_fields[FileStoreProp.NAME] = os.path.basename(
                    STORE_FILE_NAME)
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
