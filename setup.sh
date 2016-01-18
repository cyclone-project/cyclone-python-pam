#!/bin/bash
apt-get install python-dev python-pip -y

# copy the files to the proper place
cd /lib/security
git clone https://github.com/cyclone-project/cyclone-python-pam.git .
pip install -r requirements.pip


