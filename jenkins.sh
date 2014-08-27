#!/usr/bin/env bash

V_ENV_NAME="captain-venv"
virtualenv ${V_ENV_NAME}
source "${V_ENV_NAME}/bin/activate"

echo "Doing Pip Installs"
pip install -q -r requirements.txt
pip install -q -r requirements-tests.txt
rm -fr target
mkdir target
nosetests --with-xunit --xunit-file=target/nosetests.xml --with-xcover --xcoverage-file=target/coverage/coverage.xml --cover-package=captain --cover-erase --cover-html-dir=target/coverage --cover-html

deactivate
rm -fr ${V_ENV_NAME}