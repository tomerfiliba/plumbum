#!/bin/bash -e

echo $TRAVIS_PYTHON_VERSION

pip$PY3 install --upgrade pip
pip$PY3 install --upgrade -r dev-requirements.txt
pip$PY3 install coveralls
python$PY3 ./setup.py bdist_wheel
pip$PY3 install --upgrade ./dist/*.whl

echo NoHostAuthenticationForLocalhost yes >> ~/.ssh/config
echo StrictHostKeyChecking no >> ~/.ssh/config
ssh-keygen -q -f ~/.ssh/id_rsa -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
