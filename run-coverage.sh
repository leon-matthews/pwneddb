#!/bin/bash

# Run tests on application.
# Show coverage report if all tests pass.

# From the excellent Ned Batchelder
# https://coverage.readthedocs.io/

set -o nounset
set -o errexit
set +o xtrace


# Usage
if [ $# -ne 0 ]; then
    echo "Produce a coverage report for unit tests"
    echo "usage: $0"
    exit 1
fi


# Coverage from virtualenv
COVERAGE=coverage


# Run unit tests under the supervision of 'coverage.py'
$COVERAGE run --branch --module unittest --failfast --catch
$COVERAGE report --show-missing
rm -f .coverage
