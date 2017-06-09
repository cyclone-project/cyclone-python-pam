#!/usr/bin/env bash

/usr/bin/rpm -q -f /usr/bin/rpm > /dev/null 2> /dev/null
if [ $? -eq 0 ]; then
    isFedora=0
    package="yum"
    dev="devel"
    ${package} install epel-release -y
else
    isFedora=1
    package="apt-get"
    dev="dev"
fi

# Install pip
# Install all required libraries (for both Debian and RHEL systems)
${package} update
${package} install -y \
          python-${dev} \
          python-pip \
          libpam-python \
          git \
          gcc \
          libxml2-${dev} \
          libxslt-${dev} \
          openssl-${dev}

# Clone and install python package dependencies
cd /tmp && rm -rf cyclone-python-pam
git clone https://github.com/cyclone-project/cyclone-python-pam.git && cd cyclone-python-pam
git checkout CentOS
pip install -r requirements.pip

# Install python script and config
cp usr/local/bin/cyclone_pam.py /usr/local/bin/cyclone_pam.py
mkdir /etc/cyclone/
cp etc/cyclone/cyclone.conf /etc/cyclone/cyclone.conf
cp etc/cyclone/authenticated.html /etc/cyclone/authenticated.html
if [ ${isFedora} ]; then
    cp etc/pam.d/sshd-centos /etc/pam.d/sshd
    cp etc/ssh/sshd_config-centos /etc/ssh/sshd_config
    cp usr/lib64/security/pam_python-centos.so /usr/lib64/security/pam_python.so
else
    cp etc/pam.d/sshd-ubuntu /etc/pam.d/sshd
    cp etc/ssh/sshd_config-ubuntu /etc/ssh/sshd_config

fi
service sshd restart


##################
## INSTALL XPRA ##
##################
# Install only if we have the XPRA_INSTALL ENV variable set
if [ ! -z "$XPRA_INSTALL" ]; then
    if [ ! ${isFedora} ]; then
        # Install xPra for Debian systems
        curl http://winswitch.org/gpg.asc | apt-key add -
        echo "deb http://winswitch.org/ xenial main" > /etc/apt/sources.list.d/winswitch.list
        ${package} install -y software-properties-common
        add-apt-repository universe
        ${package} update
        ${package} install -y xpra

        # Install xFce
        # TODO make it possible to change the window manager
        ${package} install -y xfce4

        # Start xPra at start and execute it now (need to update to use random local internal port!)
        cp etc/rc.local /etc/rc.local
        chmod +x /etc/rc.local
    else
        # Install xPra for RHEL systems
        rpm --import https://winswitch.org/gpg.asc
        cd /etc/yum.repos.d/
        yum install -y curl
        curl -O https://winswitch.org/downloads/CentOS/winswitch.repo
        yum install xpra
    fi
fi

# Clean up installation files
rm -rf /tmp/cyclone-cyclone-pam