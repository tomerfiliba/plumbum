#!/bin/bash -e

echo $TRAVIS_PYTHON_VERSION

if [[ "$(uname -s)" == 'Darwin' ]]; then
    python$PY3 -m pip install -r dev-requirements.txt
    python$PY3 -m pip install coveralls
    python$PY3 -m pip install -e .
else
    pip install -r dev-requirements.txt
    pip install coveralls
    pip install -e .
fi

echo NoHostAuthenticationForLocalhost yes >> ~/.ssh/config
echo StrictHostKeyChecking no >> ~/.ssh/config
ssh-keygen -q -f ~/.ssh/id_rsa -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
