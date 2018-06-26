class FileStoreProp(object):
    """
    Attributes associated with the parameters for a file store operation.
    """
    ID = "file_id"
    NAME = "name"
    SIZE = "size"
    HASH_SHA256 = "hash_sha256"

    SEGMENT_NUMBER = "segment_number"
    SEGMENTS_RECEIVED = "segments_received"

    RESULT = "result"


class FileStoreResultProp(object):
    """
    Attributes associated with the results for a file store operation.
    """
    CANCEL = "cancel"
    STORE = "store"
