#!/bin/sh

# Runs the unit tests.
#
# Usage examples:
#   bin/test.sh
#   bin/test.sh tests/test_basics.py
#   bin/test.sh tests/test_convert.py::TestConvert::test2DStringArray

set -e

dir=$(dirname "$0")
cd "$dir/.."

if [ $# -gt 0 ]
then
  uv run python -m pytest -v -p no:faulthandler $@
else
  uv run python -m pytest -v -p no:faulthandler tests/
fi
