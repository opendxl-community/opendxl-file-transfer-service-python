from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import sys
import time

from dxlclient.client_config import DxlClientConfig
from dxlclient.client import DxlClient
from dxlclient.service import ServiceRegistrationInfo
from dxlbootstrap.util import MessageUtils
from dxlfiletransferclient import FileTransferClient
from dxlfiletransferservice.requesthandlers import FileStoreRequestCallback

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

# The topic for the service to respond to
SERVICE_TOPIC = "/file-transfer-sample/basic-service"

# The directory under which to store files
STORE_DIR = ""
if not STORE_DIR:
    print("'STORE_DIR' should be set to a non-empty value")
    exit(1)

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


# As the response is received from the service for each file segment
# which is transmitted, update a percentage complete counter to show
# progress
def update_progress(segment_response):
    total_segments = segment_response.total_segments
    segment_number = segment_response.segments_received
    sys.stdout.write("\rPercent complete: {}%".format(
        int((segment_number / total_segments) * 100)
        if total_segments else 100))
    sys.stdout.flush()

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
