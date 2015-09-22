#!/bin/bash -e

if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update
    brew install python$PYVER
    pip install pytest nose
    pip$PYVER install paramiko
    pip$PYVER install .
else
    pip install paramiko || true
    pip install .
fi

echo NoHostAuthenticationForLocalhost yes >> ~/.ssh/config
echo StrictHostKeyChecking no >> ~/.ssh/config
ssh-keygen -q -f ~/.ssh/id_rsa -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
cd tests
