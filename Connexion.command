#!/bin/bash
# Opens Brainy's browser so you can sign in once (Doctolib by default).
cd "$(dirname "$0")" && exec .venv/bin/python -m brainy.app --login "$@"
