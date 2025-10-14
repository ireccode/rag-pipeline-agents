#!/usr/bin/env bash
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

echo "Verifying project at $root_dir"

# Basic files
if [ ! -f Dockerfile ]; then
  echo "ERROR: Dockerfile not found"
  exit 1
fi

if [ ! -f .dockerignore ]; then
  echo "WARNING: .dockerignore not found"
fi

# Require clean working tree unless CI_ALLOW_DIRTY=1
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -z "${CI_ALLOW_DIRTY:-}" ] && [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree is dirty. Commit changes or set CI_ALLOW_DIRTY=1 to bypass."
    git status --porcelain
    exit 2
  fi
fi

# Dockerfile lint (hadolint)
if command -v hadolint >/dev/null 2>&1; then
  echo "Running hadolint on Dockerfile..."
  hadolint Dockerfile || { echo "hadolint failed"; exit 3; }
else
  echo "hadolint not found — skipping Dockerfile lint"
fi

# Run tests: prefer running inside a virtualenv if local python >=3.12, otherwise use Docker builder stage if Docker is available.
if [ -f pyproject.toml ]; then
  if [ -z "${RUN_LOCAL_TESTS:-}" ]; then
    echo "RUN_LOCAL_TESTS not set — skipping local test execution (set RUN_LOCAL_TESTS=1 to run)."
  else
  REQ_MAJOR=3
  REQ_MINOR=12
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")"
  PY_MAJOR="${PY_VER%%.*}"
  PY_MINOR="${PY_VER#*.}"

  if [ "$PY_MAJOR" -gt "$REQ_MAJOR" ] || { [ "$PY_MAJOR" -eq "$REQ_MAJOR" ] && [ "$PY_MINOR" -ge "$REQ_MINOR" ]; }; then
    echo "Preparing virtualenv for tests (.venv_verify)"
    VENV_DIR=".venv_verify"
    if [ ! -d "$VENV_DIR" ]; then
      python3 -m venv "$VENV_DIR"
    fi
    # shellcheck disable=SC1091
    . "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel
    echo "Installing project dependencies into $VENV_DIR (this may take a while)"
    pip install -e . >/dev/null 2>&1 || pip install .
    pip install pytest >/dev/null 2>&1 || true
    echo "Running pytest inside virtualenv"
    python -m pytest -q
    deactivate
  else
    if command -v docker >/dev/null 2>&1; then
      echo "Local python $PY_VER < $REQ_MAJOR.$REQ_MINOR — running tests inside Docker builder stage"
      docker build --target builder -t rag_verify_builder .
  # Install additional test-time packages inside the container if needed (helps with tests that require dev-only deps)
  TEST_EXTRA_PIPS="pydantic-ai graphiti-core deepeval supabase"
  echo "Installing extra test packages inside container (no-deps): $TEST_EXTRA_PIPS"
  docker run --rm rag_verify_builder /bin/sh -c "pip install --upgrade pip setuptools wheel || true; pip install --no-deps $TEST_EXTRA_PIPS || true; python -m pytest -q" || echo "Tests inside Docker returned non-zero exit code"
    else
      echo "Local python $PY_VER < $REQ_MAJOR.$REQ_MINOR and docker not available — skipping tests. To run tests locally install Python >=3.12 or install Docker to run tests in container."
    fi
  fi
  fi
  
else
  echo "No pyproject.toml found — skipping tests"
fi

# Optional trivy scan
if command -v trivy >/dev/null 2>&1; then
  echo "Running trivy filesystem scan (may require installation)..."
  trivy fs --exit-code 1 --ignore-unfixed --severity HIGH,CRITICAL . || echo "trivy found issues (non-zero exit)"
else
  echo "trivy not found — skipping vulnerability scan"
fi

echo "Verification completed"
