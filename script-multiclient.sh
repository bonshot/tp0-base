#!/bin/bash

# This script will run as many clients as you want with docker!
# All this using the same config as docker-compose-dev.yaml defined in the root of the project.
# This will generate a file called "`docker-compose.yaml`" using N containers for clients.

# Usage: ./script-multiclient.sh N

CONTAINERS_NUMBER=$1
FILE="docker-compose.yaml"

if [ -z "$CONTAINERS_NUMBER" ]; then
  echo "Please provide the number of containers to run"
  exit 1
fi

echo "version: '3.9'" > $FILE
echo "name: tp0" >> $FILE
echo "services:" >> $FILE
echo "  server:" >> $FILE
echo "    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
      - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net
    volumes:
      - config-volume:/config
    " >> $FILE

for i in $(seq 1 $CONTAINERS_NUMBER); do
    echo "  client$i:" >> $FILE
    echo "    container_name: client$i
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=$i
      - CLI_LOG_LEVEL=DEBUG
    networks:
      - testing_net
    depends_on:
      - server
    volumes:
      - config-volume:/config
    " >> $FILE
done

echo "networks:" >> $FILE
echo "  testing_net:" >> $FILE
echo "    ipam:" >> $FILE
echo "      driver: default" >> $FILE
echo "      config:" >> $FILE
echo "        - subnet: 172.25.125.0/24" >> $FILE

echo "volumes:" >> $FILE
echo "  config-volume:" >> $FILE
echo "    external: true" >> $FILE


