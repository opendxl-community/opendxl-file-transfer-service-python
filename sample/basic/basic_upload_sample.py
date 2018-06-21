from __future__ import absolute_import
from __future__ import print_function
import hashlib
import os
import sys
import time

from dxlclient.client_config import DxlClientConfig
from dxlclient.client import DxlClient
from dxlclient.message import Message, Request
from dxlbootstrap.util import MessageUtils
from dxlfiletransferservice.constants import FileUpload

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

UPLOAD_FILE = __file__
MAX_SEGMENT_SIZE = 500

# Create the client
with DxlClient(config) as client:
    # Connect to the fabric
    client.connect()

    logger.info("Connected to DXL fabric.")

    start = time.time()

    request_topic = "/opendxl-file-transfer/service/file-transfer/file/upload/create"
    create_request = Request(request_topic)

    file_size = os.path.getsize(UPLOAD_FILE)
    segments = file_size // MAX_SEGMENT_SIZE
    if file_size % MAX_SEGMENT_SIZE:
        segments += 1

    MessageUtils.dict_to_json_payload(create_request, {
        FileUpload.FILE_NAME: os.path.basename(UPLOAD_FILE),
        FileUpload.FILE_SIZE: file_size,
        FileUpload.FILE_TOTAL_SEGMENTS: segments
    })

    create_response = client.sync_request(create_request, timeout=30)
    if create_response.message_type == Message.MESSAGE_TYPE_ERROR:
        print("Error invoking service with topic '{}': {} ({})".format(
            request_topic, create_response.error_message,
            create_response.error_code))
        exit(1)

    create_response_dict = MessageUtils.json_payload_to_dict(create_response)
    print("Response to the upload create request: '{}'".
          format(MessageUtils.dict_to_json(create_response_dict,
                                           pretty_print=True)))
    file_id = create_response_dict[FileUpload.FILE_ID]

    request_topic = "/opendxl-file-transfer/service/file-transfer/file/upload/segment"

    file_hash = hashlib.md5()
    with open(UPLOAD_FILE, 'rb') as file_handle:
        segment = file_handle.read(MAX_SEGMENT_SIZE)
        segment_number = 0
        while segment:
            segment_request = Request(request_topic)
            file_hash.update(segment)
            segment_number += 1
            segment_request.other_fields = {
                FileUpload.FILE_ID: file_id,
                FileUpload.FILE_SEGMENT_NUMBER: str(segment_number)
            }
            segment_request.payload = segment
            segment_response = client.sync_request(segment_request, timeout=30)
            if segment_response.message_type == Message.MESSAGE_TYPE_ERROR:
                print(
                    "Error invoking service with topic '{}': {} ({})".format(
                        request_topic, segment_response.error_message,
                        segment_response.error_code))
                exit(1)
            segment_response_dict = MessageUtils.json_payload_to_dict(
                segment_response)
            logger.debug("Response to the upload segment request: '%s'",
                         MessageUtils.dict_to_json(segment_response_dict,
                                                   pretty_print=True))
            segment = file_handle.read(MAX_SEGMENT_SIZE)

    request_topic = "/opendxl-file-transfer/service/file-transfer/file/upload/complete"
    complete_request = Request(request_topic)

    MessageUtils.dict_to_json_payload(complete_request, {
        FileUpload.FILE_ID: file_id,
        FileUpload.FILE_HASH: file_hash.hexdigest()
    })

    complete_response = client.sync_request(complete_request, timeout=30)
    if complete_response.message_type != Message.MESSAGE_TYPE_ERROR:
        complete_response_dict = MessageUtils.json_payload_to_dict(
            complete_response)
        print("Response to the upload complete request: '{}'".format(
            MessageUtils.dict_to_json(complete_response_dict,
                                      pretty_print=True)))
    else:
        print("Error invoking service with topic '{}': {} ({})".format(
            request_topic, complete_response.error_message,
            complete_response.error_code))
        exit(1)

    print("Elapsed time (ms): {}".format((time.time() - start) * 1000))
