DOCKER_IMAGE ?= rag-pipeline-agents:dev
DOCKERFILE ?= Dockerfile
BUILD_ARGS ?=

.PHONY: docker-verify docker-build test

docker-verify:
	@bash ./scripts/verify_before_docker.sh

docker-build: docker-verify
	@echo "Building Docker image ${DOCKER_IMAGE}..."
	DOCKER_BUILDKIT=1 docker build --progress=plain -f ${DOCKERFILE} -t ${DOCKER_IMAGE} ${BUILD_ARGS} .

test:
	@VENV_DIR=.venv_verify; \
	if [ ! -d "$$VENV_DIR" ]; then python3 -m venv "$$VENV_DIR"; fi; \
	. "$$VENV_DIR/bin/activate"; \
	pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true; \
	pip install -e . >/dev/null 2>&1 || pip install . >/dev/null 2>&1 || true; \
	pip install pytest >/dev/null 2>&1 || true; \
	python -m pytest -q
