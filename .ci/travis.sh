#!/bin/bash -e

if [[ "$(uname -s)" == 'Darwin' ]]; then
    if brew ls --versions python$PY3 > /dev/null; then
        echo "Brew python is already installed"
    else
        brew update
        brew install python$PY3
    fi
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
