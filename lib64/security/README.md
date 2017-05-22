## Compiling `pam_python` to CentOS

In Debian based systems, the library can be fetched with any package manager. However, in CentOS systems
the library needs to be compiled from scratch. Also, it requires a patch in order to work as otherwise GCC
complains about some redeclared variables.

### Building and installing

1. Install required packages
```bash
yum install -y python-sphinx \
    gcc \
    pam-devel \
    python-devel
```

2. Obtain source
```bash
wget https://downloads.sourceforge.net/project/pam-python/pam-python-1.0.6-1/pam-python_1.0.6.orig.tar.gz
tar xvfz pam-python_1.0.6.orig.tar.gz && cd pam-python-1.0.6/
```
3. Patch for CentOS. Add `#undef  _XOPEN_SOURCE` inside `src/pam_python.c` in line 41, just over `#undef  _POSIX_C_SOURCE`

4. Build the library and install it (in the wrong folder...)
`make && make install`

5. The library can be either found in the `src/build/lib.linux-x86_64-2.7` folder or in `/lib/security` folder. 
However, the library needs to be located or symlinked to `/lib64/security/pam_python.so` so the ssh process can 
locate it.
