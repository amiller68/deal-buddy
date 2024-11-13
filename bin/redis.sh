#!/usr/bin/env bash
# NOTE:
# One stop shop for managing the Redis instance.
# Use helper functions for sourcing configs, starting, stopping, etc.
set -o errexit
set -o nounset

REDIS_CONTAINER_NAME="deal-buddy-redis"
REDIS_VOLUME_NAME="deal-buddy-redis-data"
REDIS_HOST="localhost"
REDIS_PORT="6379"

# Connection string for Redis
REDIS_ENDPOINT="redis://${REDIS_HOST}:${REDIS_PORT}"

REDIS_IMAGE_NAME="redis:latest"
CONTAINER_RUNTIME="podman"

if which docker &>/dev/null; then
    CONTAINER_RUNTIME="docker"
fi

function endpoint {
    echo ${REDIS_ENDPOINT}
}

function run {
    start-redis-container
}

# Helpers:
function start-redis-container {
    ensure-redis-container-exists
    ${CONTAINER_RUNTIME} start ${REDIS_CONTAINER_NAME}
}

function ensure-redis-container-exists {
    ${CONTAINER_RUNTIME} pull ${REDIS_IMAGE_NAME}
    create-redis-container
}

function create-redis-container {
    if ${CONTAINER_RUNTIME} ps -a | grep ${REDIS_CONTAINER_NAME} &>/dev/null; then
        return
    fi
    ${CONTAINER_RUNTIME} volume create ${REDIS_VOLUME_NAME} || true
    ${CONTAINER_RUNTIME} run \
        --name ${REDIS_CONTAINER_NAME} \
        --publish ${REDIS_PORT}:6379 \
        --volume ${REDIS_VOLUME_NAME}:/data \
        --detach \
        ${REDIS_IMAGE_NAME} redis-server --appendonly yes
}

function clean() {
    ${CONTAINER_RUNTIME} stop ${REDIS_CONTAINER_NAME} || true
    ${CONTAINER_RUNTIME} rm -fv ${REDIS_CONTAINER_NAME} || true
    ${CONTAINER_RUNTIME} volume rm -f ${REDIS_VOLUME_NAME} || true
}

$1 