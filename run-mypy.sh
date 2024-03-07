#!/bin/bash

# Run 'mypy' static type-checker over module and test code
# http://www.mypy-lang.org/

set -o nounset
set -o errexit
set +o xtrace


mypy --sqlite-cache --strict .
