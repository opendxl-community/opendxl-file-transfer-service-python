# File Transfer DXL Python service
[![OpenDXL Bootstrap](https://img.shields.io/badge/Built%20With-OpenDXL%20Bootstrap-blue.svg)](https://github.com/opendxl/opendxl-bootstrap-python)
[![Build Status](https://travis-ci.org/jbarlow-mcafee/opendxl-file-transfer-service-python.png?branch=master)](https://travis-ci.org/jbarlow-mcafee/opendxl-file-transfer-service-python)

## Overview

The File Transfer DXL Python service provides the ability to store files
via the [Data Exchange Layer](http://www.mcafee.com/us/solutions/data-exchange-layer.aspx)
(DXL) fabric. OpenDXL brokers are configured by default to limit the maximum
size of a message to 1 MB. The File Transfer DXL Python service allows the
contents of a file to be transferred in segments small enough to fit into a DXL
message. This service could be used for infrequently transferring larger file
payloads while keeping the broker's maximum message size configured at a
reasonable value for typical application workloads.

## Documentation

See the [Wiki](https://github.com/jbarlow-mcafee/opendxl-file-transfer-service-python/wiki)
for an overview of the File Transfer API DXL Python service and usage examples.

See the
[File Transfer DXL Python service documentation](https://jbarlow-mcafee.github.io/opendxl-file-transfer-service-python/pydoc)
for installation instructions, API documentation, and usage examples.

## Installation

To start using the File Transfer DXL Python Service:

* Download the [Latest Release](https://github.com/jbarlow-mcafee/opendxl-file-transfer-service-python/releases)
* Extract the release .zip file
* View the `README.html` file located at the root of the extracted files.
  * The `README` links to the documentation which includes installation
    instructions and usage examples.

## Docker Support

A pre-built Docker image can be used as an alternative to installing a Python
environment with the modules required for the File Transfer DXL service.

See the
[Docker Support Documentation](https://jbarlow-mcafee.github.io/opendxl-file-transfer-service-python/pydoc/docker.html)
for details.

## Bugs and Feedback

For bugs, questions and discussions please use the
[GitHub Issues](https://github.com/jbarlow-mcafee/opendxl-file-transfer-service-python/issues).

## LICENSE

Copyright 2018
