# Default recipe to display help
default:
    @just --list

# Python executable
python := "python3"

# Browser command using Python script
browser := python + ' -c "import os, webbrowser, sys; from urllib.request import pathname2url; webbrowser.open(\"file://\" + pathname2url(os.path.abspath(sys.argv[1])))"'

# Remove all build, test, coverage and Python artifacts
clean: clean-build clean-pyc clean-test

# Remove build artifacts
clean-build:
    rm -fr build/
    rm -fr dist/
    rm -fr .eggs/
    find . -name '*.egg-info' -exec rm -fr {} +
    find . -name '*.egg' -exec rm -f {} +

# Remove Python file artifacts
clean-pyc:
    find . -name '*.pyc' -exec rm -f {} +
    find . -name '*.pyo' -exec rm -f {} +
    find . -name '*~' -exec rm -f {} +
    find . -name '__pycache__' -exec rm -fr {} +
    find . -name '*.so' -exec rm -f {} +
    find . -name '*.c' -exec rm -f {} +

# Remove test and coverage artifacts
clean-test:
    rm -fr .tox/
    rm -f .coverage
    rm -fr htmlcov/
    rm -fr .pytest_cache


# Check style with flake8
lint:
    flake8 .

# Fix style with autopep8 and isort
lint-fix:
    autopep8 . --in-place --aggressive --aggressive --aggressive --recursive --ignore=W191,E101,E111,E122
    isort .

# Run tests quickly with the default Python
test:
    pytest

# Run tests on every Python version with tox
test-all:
    tox

# Check code coverage quickly with the default Python
coverage:
    coverage run --source imagehash -m pytest
    coverage report -m
    coverage html
    # {{browser}} htmlcov/index.html


# Package and upload a release
release: dist
    twine upload -s dist/*.tar.gz dist/*.whl

# Build source and wheel package
dist: clean
    {{python}} setup.py sdist
    {{python}} setup.py bdist_wheel
    ls -l dist

# Install the package to the active Python's site-packages
install: clean
    {{python}} setup.py install
