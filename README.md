# PwnedDB

Utility to aid research of user password behaviour with the database of
password popularity from [';-) have i been pwned](https://haveibeenpwned.com/).

The three roles this utility provides are:

1. Download the password database and keep it up-to-date.
2. Merge plain-text passwords where possible.
3. Query the resulting database for summary statistics and patterns.


## Background

API usage requires a five-character prefix.

    GET https://api.pwnedpasswords.com/range/5baa6
    ...
    048A3DC99E0FA445B1C94A72E8AA07FDCD8:1
    04A37A676E312CC7C4D236C93FBD992AA3C:10
    04AE045B134BDC43043B216AEF66100EE00:3
    04F32798194C1D127211AB0E374FF4EDE91:1
    0502EA98ED7A1000D932B10F7707D37FFB4:6
    0525D5F07ADA8526E75A3D05AD76DB1F3CA:1
    0539F86F519AACC7030B728CD47803E5B22:6
    ...

Note that the given prefix must be combined with the requested suffixes
to get full SHA-1 hashes.


## Create PYZ release

    $ pyc
    $ trash .mypy_cache
    $ trash ~/Temp/pwned_passwords*
    $ cp -a pwned_passwords/ ~/Temp/pwned_passwords/
    $ pip install requests==2.28.2 sqlalchemy==2.0.9 --target ~/Temp/pwned_passwords/
    $ python3 -m zipapp --compress ~/Temp/pwned_passwords/ --python '/usr/bin/env python3'
    $ scp ~/Temp/pwned_passwords.pyz ming.local:
