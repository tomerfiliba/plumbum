#!/bin/bash -e

if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update
    brew install python$PY3
    pip$PY3 install pytest nose
    pip$PY3 install paramiko
    pip$PY3 install .
else
    pip install paramiko || true
    pip install .
fi

echo NoHostAuthenticationForLocalhost yes >> ~/.ssh/config
echo StrictHostKeyChecking no >> ~/.ssh/config
ssh-keygen -q -f ~/.ssh/id_rsa -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
