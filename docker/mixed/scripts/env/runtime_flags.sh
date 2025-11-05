#!/usr/bin/env bash

# Default concurrent mode ON for Docker; user can set CONCURRENT_MODEL_CALL=0 for sequential
export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}


