VERSION = "0.1.0"

.DEFAULT_GOAL := help
help: 
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Version Management
.PHONY: patch minor major
patch: 
	uvx bumpversion patch
minor: 
	uvx bumpversion minor
major: 
	uvx bumpversion major

format:
	uvx black thoughtlocker/*.py

build: format
	uv lock
	uv build

install: build 
	uv sync
	uv sync --group dev
	uv pip install -e .

clean:
	rm -rf dist build thoughtlocker.egg-info
	git clean -fdx -e .venv/ -e .pixi/ -e '*.pyc' -e '*.pyo' -e '__pycache__'

uninstall:
	pip uninstall thoughtlocker -y
	uv pip uninstall -y thoughtlocker

publish: build
	uv publish
	git push origin --tags
