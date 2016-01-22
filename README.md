## Synopsis

This project is a python written PAM module which enables users to login using their eduGAIN federated login account.
To do so, it creates a new PAM library using Python's [pam-python](http://pam-python.sourceforge.net/) module.
This spawns a HTTP server in a random port which allows the user to login using their eduGAIN enabled account, from where
when receiving the callback we retrieve the user details from a JWT string and authenticate the user against a white-list.

## Motivation

The main motivation for this module is to replace the somewhat tricky configuration of the ssh module, as for non IT people
it can be slightly difficult to create a private/public key and deploy it to the server. With this project we intend to 
provide a simple, fast and secure way to login into a server.

## Installation

### Manual configuration

In order to work properly, cyclone-pam-module fetches the hostname of the machine and uses it as a base of the URL to do 
the callbacks to this machine.
Make sure that the hostname matches with an accessible URL to the machine. In the future this variable will be available
from the SlipStream ENV variables configuration.

You can setup your custom hostname in the machine with `sudo hostname your-new-name`

### Automatic setup script

The easiest way to install the project is fetching setup.sh in your machine and execute it.
It will clone the project, install everything and clean the unnecessary files for you.

You can use the next oneliner as superuser to execute the setup script:

`wget -O - https://raw.githubusercontent.com/cyclone-project/cyclone-python-pam/master/setup.sh | bash`
**For some reason, seems that the script needs to be run twice. It tries to execute the bash script before ending the apt-get command...** 

The next steps are the ones that the setup script does when executed:

1. Install python-dev and python-pip
`apt-get install python-dev python-pip -y`
This will install pam_python.so in `/lib/security` and the necessary python dev packages
2. Copy python script (cyclone_pam.py) and its configuration (cyclone_pam.config) to `/lib/security`
3. Install required pyton packages listed in `requirements.pip` 
4. Replace sshd PAM configuration in `/etc/pam.d/sshd` with the updated version in this repository (`./etc/pam.d/sshd`)
This replaces the default UNIX authentication for our own custom federated authentication.
It could be improved so it falls back to usual authentication if it fails.
5. Update sshd configuration in `/etc/ssh/sshd_config` with the updated version in this repository (`./etc/ssh/sshd_config`)and restart `service sshd restart`
**Needed configuration changes**:
    * UsePrivilegeSeparation yes : make sure the user doesn't execute not wanted code
    * PubkeyAuthentication yes : allow login with public key
    * ChallengeResponseAuthentication yes : specifies whether to use challenge-response authentication.
    * PasswordAuthentication no : we disable password authentication to replace it with our own authentication
    * UsePAM yes : we need PAM enabled so it uses our PAM module
    * PermitRootLogin yes : **Enable only if you want to allow root login through ssh**



## References

* Atlassian Crowd PAM module: https://github.com/tomoconnor/pam_python_crowd
* Digital Ocean OTPW configuration tutorial: https://www.digitalocean.com/community/tutorials/install-and-use-otpw
* PAM documentation (functions and arguments interface): http://www.linux-pam.org/Linux-PAM-html/adg-interface-by-app-expected.html 
* pam-python module documentation: http://pam-python.sourceforge.net/doc/html/

## Debugging the project

The best way to debug the module is to send back information to the SSH using messages (see examples in the code)
This will print the variable information into the SSH login screen.

For the server itself, it could be ran separately and tested as a usual Python script.
