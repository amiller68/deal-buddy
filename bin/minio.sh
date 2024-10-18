#!/usr/bin/env bash
# NOTE:
# One stop shop for managing the MinIO object storage.
# Use helper functions for sourcing configs, starting, stopping, etc.
set -o errexit
set -o nounset

MINIO_CONTAINER_NAME="deal-buddy-minio"
MINIO_VOLUME_NAME="deal-buddy-minio-data"
MINIO_ROOT_USER="minioadmin"
MINIO_ROOT_PASSWORD="minioadmin"
MINIO_HOST="localhost"
MINIO_PORT="9000"
MINIO_CONSOLE_PORT="9001"

# Connection string for MinIO
MINIO_ENDPOINT="http://${MINIO_HOST}:${MINIO_PORT}"

MINIO_IMAGE_NAME="minio/minio:latest"
CONTAINER_RUNTIME="podman"

if which docker &>/dev/null; then
    CONTAINER_RUNTIME="docker"
fi

function endpoint {
    echo ${MINIO_ENDPOINT}
}

function run {
    start-minio-container
}

# Helpers:
function start-minio-container {
    ensure-minio-container-exists
    ${CONTAINER_RUNTIME} start ${MINIO_CONTAINER_NAME}
}

function ensure-minio-container-exists {
    ${CONTAINER_RUNTIME} pull ${MINIO_IMAGE_NAME}
    create-minio-container
}

function create-minio-container {
    if ${CONTAINER_RUNTIME} ps -a | grep ${MINIO_CONTAINER_NAME} &>/dev/null; then
        return
    fi
    ${CONTAINER_RUNTIME} volume create ${MINIO_VOLUME_NAME} || true
    ${CONTAINER_RUNTIME} run \
        --name ${MINIO_CONTAINER_NAME} \
        --env MINIO_ROOT_USER=${MINIO_ROOT_USER} \
        --env MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD} \
        --publish ${MINIO_PORT}:9000 \
        --publish ${MINIO_CONSOLE_PORT}:9001 \
        --volume ${MINIO_VOLUME_NAME}:/data \
        --detach \
        ${MINIO_IMAGE_NAME} server /data --console-address ":9001"
}

function clean() {
    ${CONTAINER_RUNTIME} stop ${MINIO_CONTAINER_NAME} || true
    ${CONTAINER_RUNTIME} rm -fv ${MINIO_CONTAINER_NAME} || true
    ${CONTAINER_RUNTIME} volume rm -f ${MINIO_VOLUME_NAME} || true
}

$1