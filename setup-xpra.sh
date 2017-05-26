#!/bin/bash

## INSTALL XPRA

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
