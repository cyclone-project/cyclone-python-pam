#!/bin/bash

# Install pip
# Installs python_pam.so in /lib/security
apt-get update
apt-get install python-dev python-pip libpam-python git -y

# Clone and install python package dependencies
cd /tmp
git clone https://github.com/cyclone-project/cyclone-python-pam.git . && cd cyclone-python-pam
git checkout V2
pip install -r requirements.pip

# Install python script and config
cp usr/local/bin/cyclone_pam.py /usr/local/bin/cyclone_pam.py
cp etc/cyclone/cyclone.conf /etc/cyclone/cyclone.conf
cp etc/cyclone/authenticated.html /etc/cyclone/authenticated.html
cp etc/pam.d/sshd /etc/pam.d/sshd
cp etc/ssh/sshd_config /etc/ssh/sshd_config
service ssh restart

## INSTALL XPRA

# Install only if we have the XPRA_INSTALL ENV variable
if [ -z "$XPRA_INSTALL" ]; then
    # Install xPra latest version from WinSwitch repo
    curl http://winswitch.org/gpg.asc | apt-key add -
    echo "deb http://winswitch.org/ xenial main" > /etc/apt/sources.list.d/winswitch.list
    apt-get install -y software-properties-common
    add-apt-repository universe
    apt-get update
    apt-get install -y xpra
    # Install xFce
    apt-get install -y xfce4

    # Start xPra at start and execute it now (need to update to use random local internal port!)
    cp etc/rc.local /etc/rc.local
    chmod +x /etc/rc.local
fi

# Clean up installation files
#cd /tmp && rm -rf cyclone-cyclone-pam
