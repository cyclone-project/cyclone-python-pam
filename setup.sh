#!/bin/bash

# Install pip
# Installs python_pam.so in /lib/security
apt-get update
apt-get install python-dev python-pip libpam-python git -y

# Clone and install python package dependencies
cd /tmp
git clone https://github.com/cyclone-project/cyclone-python-pam.git && cd cyclone-python-pam
git checkout V2
pip install -r requirements.pip

# Install python script and config
cp usr/local/bin/cyclone_pam.py /usr/local/bin/cyclone_pam.py
mkdir /etc/cyclone/
cp etc/cyclone/cyclone.conf /etc/cyclone/cyclone.conf
cp etc/cyclone/authenticated.html /etc/cyclone/authenticated.html
cp etc/pam.d/sshd /etc/pam.d/sshd
cp etc/ssh/sshd_config /etc/ssh/sshd_config
service ssh restart

## INSTALL XPRA

# Install only if we have the XPRA_INSTALL ENV variable
if [ ! -z "$XPRA_INSTALL" ]; then
    chmod a+x setup-xpra.sh
    ./setup-xpra.sh
fi

# Clean up installation files
#cd /tmp && rm -rf cyclone-cyclone-pam
