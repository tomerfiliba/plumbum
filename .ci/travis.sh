#!/bin/bash -e

echo $TRAVIS_PYTHON_VERSION

python$PY3 -m pip install --upgrade pip
python$PY3 -m pip install --upgrade pytest setuptools wheel
python$PY3 -m pip install -r dev-requirements.txt
python$PY3 -m pip install coveralls
python$PY3 -m pip install -e .

echo NoHostAuthenticationForLocalhost yes >> ~/.ssh/config
echo StrictHostKeyChecking no >> ~/.ssh/config
ssh-keygen -q -f ~/.ssh/id_rsa -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
