#!/bin/sh
# Simple helper to install packages required for running the test suite.
python -m pip install --upgrade pip
pip install -r requirements-test.txt
# Install this project in editable mode so tests can import it
pip install -e .
