import hashlib
import json
import os
import random
import re
import shutil
import string
import sys
import unittest
from tempfile import mkdtemp, NamedTemporaryFile

if sys.version_info[0] > 2:
    import builtins  # pylint: disable=import-error, unused-import
else:
    import __builtin__  # pylint: disable=import-error

    builtins = __builtin__  # pylint: disable=invalid-name

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

# pylint: disable=wrong-import-position
from mock import patch
from dxlfiletransferclient.constants import FileStoreProp, \
    FileStoreResultProp, HashType
import dxlfiletransferservice


class StringMatches(object):
    def __init__(self, pattern):
        self.pattern = pattern

    def __eq__(self, other):
        return re.match(self.pattern, other, re.DOTALL)


class StringDoesNotMatch(object):
    def __init__(self, pattern):
        self.pattern = pattern

    def __eq__(self, other):
        return not re.match(self.pattern, other)


class Sample(unittest.TestCase):
    _RANDOM_FILE_SIZE = 2 * (2 ** 20) # 2 MB

    _RANDOM_CHOICE_CHARS = string.ascii_uppercase + string.digits + \
                           string.punctuation + "\0\1\2\3"

    @staticmethod
    def expected_print_output(title, detail):
        json_string = title + json.dumps(detail, sort_keys=True,
                                         separators=(".*", ": "))
        return re.sub(r"(\.\*)+", ".*",
                      re.sub(r"[{[\]}]", ".*", json_string))

    @staticmethod
    def run_sample(sample_file, sample_args):
        with open(sample_file) as f, \
                patch.object(builtins, 'print') as mock_print:
            sample_globals = {"__file__": sample_file}
            original_sys_argv = sys.argv
            try:
                if sample_args:
                    sys.argv = [sample_file] + sample_args
                exec(f.read(), sample_globals)  # pylint: disable=exec-used
            finally:
                sys.argv = original_sys_argv
        return mock_print

    def run_sample_with_service(self, sample_file, sample_args, storage_dir):
        with dxlfiletransferservice.FileTransferService("sample") as app:
            config = ConfigParser()
            config.read(app._app_config_path)
            if not config.has_section(
                    dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION):
                config.add_section(
                    dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION)
            config.set(
                dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION,
                dxlfiletransferservice.FileTransferService._GENERAL_STORAGE_DIR_PROP,
                storage_dir
            )
            if config.has_option(
                    dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION,
                    dxlfiletransferservice.FileTransferService._GENERAL_WORKING_DIR_PROP
            ):
                config.remove_option(
                    dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION,
                    dxlfiletransferservice.FileTransferService._GENERAL_WORKING_DIR_PROP
                )
            if config.has_option(
                    dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION,
                    dxlfiletransferservice.FileTransferService._GENERAL_STORE_TOPIC_PROP
            ):
                config.remove_option(
                    dxlfiletransferservice.FileTransferService._GENERAL_CONFIG_SECTION,
                    dxlfiletransferservice.FileTransferService._GENERAL_STORE_TOPIC_PROP
                )
            with NamedTemporaryFile(mode="w+", delete=False) as temp_config_file:
                config.write(temp_config_file)
            app._app_config_path = temp_config_file.name
            try:
                app.run()
                mock_print = self.run_sample(sample_file, sample_args)
            finally:
                os.remove(temp_config_file.name)
            return mock_print

    def create_random_file(self):
        file_hash = hashlib.sha256()
        with NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            file_bytes = "".join([random.choice(self._RANDOM_CHOICE_CHARS)
                                  for _ in range(self._RANDOM_FILE_SIZE)])
            file_hash.update(file_bytes.encode())
            temp_file.write(file_bytes)
        return temp_file.name, file_hash.hexdigest()

    @staticmethod
    def get_hash_for_file(file_name):
        file_hash = hashlib.sha256()
        with open(file_name, "rb") as file_handle:
            file_data = file_handle.read()
            while file_data:
                file_hash.update(file_data)
                file_data = file_handle.read()
        return file_hash.hexdigest()

    @staticmethod
    def overwrite_file_line(file_name, pattern, replacement):
        with open(file_name, "r") as file_handle,\
                NamedTemporaryFile(mode="w+",
                                   dir=os.path.dirname(file_name),
                                   delete=False) as new_file:
            for line in file_handle:
                line = re.sub(pattern, replacement, line)
                new_file.write(line)
        return new_file.name

    def test_basic_store_example(self):
        storage_dir = mkdtemp()
        source_file, source_file_hash = self.create_random_file()
        store_subdir = "subdir1/subdir2"
        expected_store_file = os.path.join(
            storage_dir, store_subdir, os.path.basename(source_file)
        )
        try:
            mock_print = self.run_sample_with_service(
                "sample/basic/basic_store_example.py",
                [source_file, store_subdir], storage_dir)
            self.assertTrue(os.path.exists(expected_store_file))
            self.assertEqual(source_file_hash,
                             self.get_hash_for_file(expected_store_file))
            mock_print.assert_any_call(
                StringMatches(
                    self.expected_print_output(
                        "\nResponse to the request for the last segment:",
                        {
                            FileStoreProp.RESULT: FileStoreResultProp.STORE
                        }
                    )
                )
            )
            mock_print.assert_any_call(StringDoesNotMatch(
                "Error invoking request"))
        finally:
            os.remove(source_file)
            shutil.rmtree(storage_dir)

    def test_basic_service_example(self):
        storage_dir = mkdtemp()
        source_file, source_file_hash = self.create_random_file()
        store_subdir = "subdir1/subdir2"
        expected_store_file = os.path.join(
            storage_dir, store_subdir, os.path.basename(source_file)
        )
        sample_file = self.overwrite_file_line(
            "sample/basic/basic_service_example.py",
            r'(STORAGE_DIR = ")[^"]*',
            r"\1{}".format(storage_dir))
        try:
            mock_print = self.run_sample(sample_file,
                                         [source_file, store_subdir])
            self.assertTrue(os.path.exists(expected_store_file))
            self.assertEqual(source_file_hash,
                             self.get_hash_for_file(expected_store_file))
            mock_print.assert_any_call(
                StringMatches(
                    self.expected_print_output(
                        "\nResponse:",
                        {
                            FileStoreProp.HASHES: {
                                HashType.SHA256: source_file_hash
                            },
                            FileStoreProp.SIZE: os.path.getsize(source_file)
                        }
                    )
                )
            )
            mock_print.assert_any_call(StringDoesNotMatch(
                "Error invoking request"))
        finally:
            os.remove(sample_file)
            os.remove(source_file)
            shutil.rmtree(storage_dir)
