#!/bin/bash

# Using the docker-compose file to start the server with it's configuration and the existing network
# and no clients
docker compose -f docker-compose-server.yaml up --build -d

# Create a client container
docker run --name client_test --network tp0_testing_net -it ubuntu:latest /bin/bash -c "apt-get update && apt-get install -y netcat"

# Start the client container
docker start client_test

# Verify that the response is the same as the message sent
docker exec -it client_test /bin/bash -c "echo 'Hello buddy' | nc server 12345 | grep -q 'Hello buddy' && echo 'Test passed' || echo 'Test failed'"

# Stop and remove the containers
docker stop client_test
docker rm client_test
docker compose -f docker-compose.yaml stop -t 1
docker compose -f docker-compose.yaml down