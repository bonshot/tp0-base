#!/bin/bash
# Verifies and copy the config files to the volume if they don't exist

if ! docker run --rm -v config-volume:/config alpine test -e /config/config.ini; then
    docker run --rm -v "$(pwd)"/server/config.ini:/config2/config.ini -v config-volume:/config alpine cp /config2/config.ini /config
fi

if ! docker run --rm -v config-volume:/config alpine test -e /config/config.yaml; then
    docker run --rm -v "$(pwd)"/client/config.yaml:/config2/config.yaml -v config-volume:/config alpine cp /config2/config.yaml /config
fi