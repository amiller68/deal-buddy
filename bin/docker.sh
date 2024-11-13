#!/usr/bin/env bash
set -o errexit
set -o nounset

IMAGE_NAME="deal-buddy"
CONTAINER_NAME="deal-buddy"
CONTAINER_RUNTIME="docker"

# if podman, use podman instead of docker
# if command -v podman &>/dev/null; then
# 	CONTAINER_RUNTIME="podman"
# fi

function run {
	echo "Building image"
	ensure-image
	echo "Starting container"
	start-container
}

function build {
	ensure-image
}

function build-worker {
	ensure-worker-image
}

function ensure-image {
	docker build -t ${IMAGE_NAME} .
}

function ensure-worker-image {
	docker build -t ${IMAGE_NAME}-worker -f Dockerfile.worker .
}

function start-container {
	if ${CONTAINER_RUNTIME} ps -a | grep ${IMAGE_NAME} &>/dev/null; then
		echo "Container already exists"
		return
	fi
	${CONTAINER_RUNTIME} run \
		--name ${CONTAINER_NAME} \
		--publish 8000:8000 \
		--env-file .env.docker \
		--volume ${PWD}/data:/data \
		--detach \
		${IMAGE_NAME}
}

function start-worker-container {
	ensure-worker-image
	${CONTAINER_RUNTIME} run \
		--name ${CONTAINER_NAME}-worker \
		--env-file .env.docker \
		--volume ${PWD}/data:/data \
		--detach \
		${IMAGE_NAME}-worker
}

function clean {
	${CONTAINER_RUNTIME} stop ${CONTAINER_NAME} || true
	${CONTAINER_RUNTIME} rm -fv ${CONTAINER_NAME} || true
}

"$@"
