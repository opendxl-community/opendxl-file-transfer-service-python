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
from dxlfiletransferservice.constants import FileStoreParam

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

STORE_FILE = __file__
MAX_SEGMENT_SIZE = 500

# Create the client
with DxlClient(config) as client:
    # Connect to the fabric
    client.connect()

    logger.info("Connected to DXL fabric.")

    start = time.time()

    request_topic = "/opendxl-file-transfer/service/file-transfer/file/store"

    res_dict = {}
    with open(STORE_FILE, 'rb') as file_handle:
        file_size = os.path.getsize(STORE_FILE)
        file_hash = hashlib.md5()

        segment_number = 0
        file_id = None
        bytes_read = 0
        continue_reading = True

        while continue_reading:
            segment = file_handle.read(MAX_SEGMENT_SIZE)
            segment_number += 1

            req = Request(request_topic)
            other_fields = {
                FileStoreParam.FILE_NAME: os.path.basename(STORE_FILE),
                FileStoreParam.FILE_SEGMENT_NUMBER: str(segment_number)
            }

            if file_id:
                other_fields[FileStoreParam.FILE_ID] = file_id

            bytes_read += len(segment)
            file_hash.update(segment)
            if bytes_read == file_size:
                other_fields[FileStoreParam.FILE_RESULT] = \
                    FileStoreParam.FILE_RESULT_STORE
                other_fields[FileStoreParam.FILE_SIZE] = str(file_size)
                other_fields[FileStoreParam.FILE_HASH] = file_hash.hexdigest()

            req.other_fields = other_fields
            req.payload = segment

            res = client.sync_request(req, timeout=30)
            if res.message_type == Message.MESSAGE_TYPE_ERROR:
                print("Error invoking service with topic '{}': {} ({})".format(
                    request_topic, res.error_message, res.error_code))
                exit(1)

            res_dict = MessageUtils.json_payload_to_dict(res)
            if segment_number == 1:
                print("Response to the request for the first segment: \n{}".
                      format(MessageUtils.dict_to_json(res_dict,
                                                       pretty_print=True)))
            elif bytes_read < file_size:
                logger.debug("Response to the request for segment {}: \n{}".
                             format(segment_number,
                                    format(MessageUtils.dict_to_json(
                                        res_dict, pretty_print=True))))
            else:
                continue_reading = False

            if not file_id:
                file_id = res_dict[FileStoreParam.FILE_ID]

    print("Response to the request for the last segment: \n{}".
          format(MessageUtils.dict_to_json(res_dict, pretty_print=True)))
    print("Elapsed time (ms): {}".format((time.time() - start) * 1000))
