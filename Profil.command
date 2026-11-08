#!/bin/bash
# Opens your Brainy profile (birth date, address...) to fill it in once.
cd "$(dirname "$0")" && exec .venv/bin/python -m brainy.app --profile
