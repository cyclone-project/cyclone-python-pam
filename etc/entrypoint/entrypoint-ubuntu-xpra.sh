#!/usr/bin/env bash

# Start Xpra
su - ubuntu -c 'xpra start  --sharing=yes --xvfb="Xorg -dpi 310 -noreset -nolisten tcp +extension GLX \
    -config /etc/xpra/xorg.conf \
    +extension RANDR +extension RENDER -logfile ${HOME}/.xpra/Xorg-10.log"  --start-child=startxfce4 --html=on --bind-tcp=localhost:20001'

exit 0