#!/bin/bash
# install pip
# installs python_pam.so in /lib/security
apt-get update
apt-get install python-dev python-pip libpam-python git -y

# clone and install python package dependencies
cd ~
mkdir cyclone-pam && cd cyclone-pam
git clone https://github.com/cyclone-project/cyclone-python-pam.git .
pip install -r requirements.pip

# install python script and config
cp lib/security/cyclone_pam.py /lib/security/cyclone_pam.py
cp lib/security/cyclone_config /lib/security/cyclone_config
cp lib/security/key.pem /lib/security/key.pem

# update ssh PAM config
cp etc/pam.d/sshd /etc/pam.d/sshd

# update sshd configuration and restart service
cp etc/ssh/sshd_config /etc/ssh/sshd_config
service ssh restart

# clean installation files
cd ~ && rm -rf cyclone-pam

