#!/bin/bash

# Install pip
# Installs python_pam.so in /lib/security
apt-get update
apt-get install python-dev python-pip libpam-python git -y

# Clone and install python package dependencies
cd ~
mkdir cyclone-pam && cd cyclone-pam
git clone https://github.com/cyclone-project/cyclone-python-pam.git .
git checkout V2
pip install -r requirements.pip

# Install python script and config
cp usr/local/bin/cyclone_pam.py /usr/local/bin/cyclone_pam.py
cp --parents etc/cyclone/* /

# Update ssh PAM config
cp etc/pam.d/sshd /etc/pam.d/sshd

# Update sshd configuration and restart service
cp etc/ssh/sshd_config /etc/ssh/sshd_config
service ssh restart

# Clean installation files
cd ~ && rm -rf cyclone-pam

