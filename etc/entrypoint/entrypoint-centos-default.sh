#!/usr/bin/env bash

# Read ports from config file
config="$(cat /etc/cyclone/cyclone.conf | grep "^[^#;]" | grep PORTS | sed -e 's/^PORTS\s\?=\s\?//g')"
regex="(?:(\d+-\d+)|(\d+))(?:,\s+)?"
groups="$(grep -P $regex <<< $config)"

# Open ports in firewall
for ports in $groups
do
    port="$(sed 's/,*$//g' <<< ${ports} )"
    firewall-cmd --zone=public --add-port="${port}/tcp" --permanent
done

# Disable selinux in specific ports
# yum install -y setroubleshoot-server
# semanage port -a -t ssh_port_t -p tcp <portshere>

exit 0