## Synopsis

This project is a python written PAM module which enables users to login using their eduGAIN federated login account.
To do so, it creates a new PAM library using Python's [pam-python](http://pam-python.sourceforge.net/) module.
This spawns a HTTP server in a random port which allows the user to login using their eduGAIN enabled account, from where
when receiving the callback we retrieve the user details from a JWT string and authenticate the user against a white-list.

## Motivation

The main motivation for this module is to replace the somewhat tricky configuration of the ssh module, as for non IT people
it can be slightly difficult to create a private/public key and deploy it to the server. With this project we intend to 
provide a simple, fast and secure way to login into a server.

## How it works

 By using pam_python we can create a PAM module from where we can override the authentication procedure for any PAM enabled
 service. In this case we override the SSH configuration to allow the user to login using an SSO server as a backend.
 To do so, we include in this project a patched ssh PAM configuration (usually located in `/etc/pam.d/sshd`), that replaces
 the password authentication with the custom SSO configuration.

 To execute the SSO calls, this library relies on [PyOIDC](http://pyoidc.readthedocs.io/en/latest/), a library 
 that allows OIDC authentication with an easy approach. 
 PyOIDC relies on the public configuration exposed by Keycloak (based on optional OIDC standards) to 
 automatically configure the client with the proper configuration. An example of this file can be seen in:
 https://federation.cyclone-project.eu/auth/realms/master/.well-known/openid-configuration .
 
 If this configuration cannot be found, it could be set up to load a similar configuration file from the filesystem.
 At the moment the path to this autodiscovery configuration is created on the fly using the hostname and the realm name.
 
 By using this configuration PyOIDC authenticates following the *Authorization Workflow* in oAuth2 by using the ClientId
 and Client Secret, thus receiving a token. With this user token, we can then request an access token with which we can
 execute authenticated calls against OIDC protected endpoints. In our case we use this token to access the OIDC User Data
 endpoint, from where we can fetch information of the user, specifically the **mail** attribute.
 
 Finally, by using this mail attribute, we try to locate a `.cyclone` file in the home folder of the user, with a list of
 whitelisted mail accounts that are allowed to authenticate as this user. If there is a match between the SSO provided
 mail account and the whitelisted one, we define that the user is authorized to login. Then, we notify the PAM module
 to allow access to the user.
 
 ### Working with SELinux
 
 In order to work with SELinux we need to both open ports of the firewall and also tag this ports to be used by the SSH
  process. The final process executing this code is the SSH one, and by default SELinux restricts processes to only
  use ports tagged for their own use.

## Installation

### Manual configuration

In order to work properly, cyclone-pam-module fetches the hostname of the machine and uses it as a base of the URL to do 
the callbacks to this machine.
Other configuration options of the hostname include setting a custom hostname via the configuration file.

Also, another option has been added to allow fetching the hostname or IP from the machine using OpenStack's enpodint.
More information can be found in this module's configuration file.

### Automatic setup script

The easiest way to install the project is fetching setup.sh in your machine and execute it.
It will clone the project, install everything and clean the unnecessary files for you.

You can use the next oneliner as superuser to execute the setup script:

`wget -O - https://raw.githubusercontent.com/cyclone-project/cyclone-python-pam/master/setup.sh | sh`

The next steps are the ones that the setup script does when executed:

1. Install python-dev and python-pip
`apt-get install python-dev python-pip -y`
This will install pam_python.so in `/lib/security` and the necessary python dev packages
2. Copy python script (cyclone_pam.py) and its configuration (cyclone_pam.config) to their specified paths
(you can see them in the structure of this project)
3. Install required pyton packages listed in `requirements.pip` 
4. Replace sshd PAM configuration in `/etc/pam.d/sshd` with the updated version in this repository (`./etc/pam.d/sshd`)
This replaces the default UNIX authentication for our own custom federated authentication.
It could be improved so it falls back to usual authentication if it fails.
5. Update sshd configuration in `/etc/ssh/sshd_config` with the updated version in this repository (`./etc/ssh/sshd_config`) 
and restart `service sshd restart`
**Needed configuration changes**:
    * UsePrivilegeSeparation yes : make sure the user doesn't execute not wanted code
    * PubkeyAuthentication yes : allow login with public key
    * ChallengeResponseAuthentication yes : specifies whether to use challenge-response authentication.
    * PasswordAuthentication no : we disable password authentication to replace it with our own authentication
    * UsePAM yes : we need PAM enabled so it uses our PAM module
    * PermitRootLogin yes : **Enable only if you want to allow root login through ssh**

## Configuration
### WhiteListing
In order to determine if someone can login as a specific user we are using a whitelisting technique.
In this case, CYCLONE-PAM will search for an `.edugain` file located _in the home folder of the user_ to check if a user 
is allowed to login.

_**Example case**_

1. John Doe wants to login as user 'randomuser' so he does `ssh randomuser@host`
2. When doing SSH he logs into the given server with his EduGain account.
3. CYCLONE-PAM fetches John Doe's mail from his EduGain account data
4. CYCLONE-PAM opens the file `/home/randomuser/.cyclone` and checks that the mail provided by EduGain matches with any
of the ones found in the file.
5. If at any moment the file doesn't exist or the mail is not in the file, the authentication is rejected.

The structure of the `.cyclone` file is as followed:
```
EMAIL =  test@example.org, username@example.com
```

### Available Ports
As there are clouds and servers that have a limited range of ports available to be used because of a firewall, this 
module integrates configuration to allow
to define which ports can the service use.

To do so, edit the `/etc/cyclone/cyclone.conf` file to add your ports. 
Add single values for specific ports and a sub array with two values from min to max for ranges.

Then finally enable to load this configuration from the file changing the proper line in `/etc/pam.d/ssh` so it loads 
this configuration as an argument to the CYCLONE-PAM module.

## References

* Atlassian Crowd PAM module: https://github.com/tomoconnor/pam_python_crowd
* Digital Ocean OTPW configuration tutorial: https://www.digitalocean.com/community/tutorials/install-and-use-otpw
* PAM documentation (functions and arguments interface): http://www.linux-pam.org/Linux-PAM-html/adg-interface-by-app-expected.html 
* pam-python module documentation: http://pam-python.sourceforge.net/doc/html/

## Debugging the project

The best way to debug the module is to send back information to the SSH using messages (see examples in the code)
This will print the variable information into the SSH login screen.
Also, python errors will be excepted to the auth.log file in `/var/log/auth.log`.

For the server itself, it could be ran separately and tested as a usual Python script, executin main() function and 
enabling all the DEBUG comments.
