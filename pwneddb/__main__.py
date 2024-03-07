"""
Create and update database of passwords.
"""

import os
import signal
import sys

from pwneddb.command_line import CommandLine


def sigint_handler(signum, stack):                          # type: ignore
    raise SystemExit('Cancelled by user, aborting.')


def sigterm_handler(signum, stack):                         # type: ignore
    raise SystemExit('System shutdown detected, aborting.')


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigterm_handler)


if __name__ == '__main__':
    print('My PID is:', os.getpid())
    main = CommandLine(sys.argv[1:])
    sys.exit(main.run())
