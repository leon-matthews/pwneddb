
import argparse
import logging
import os
from pathlib import Path
import sys
import time

from . import utils
from .db import connect
from .updatinator import Updatinator


logger = logging.getLogger(__name__)


class Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """
        Change formatting depending on level of message.
        """
        if record.levelno <= logging.DEBUG:
            self._style._fmt = "    %(message)s"
        elif record.levelno <= logging.INFO:
            self._style._fmt = "  %(message)s"
        else:
            self._style._fmt = "%(asctime)s %(message)s"

        return super().format(record)


class CommandLine:
    """
    Command-line interface to whole program.
    """
    def __init__(self, arguments: list[str]):
        parser = self.make_parser()
        self.options = parser.parse_args(arguments)
        self.configure_logging()
        self.terminal_width, _ = os.get_terminal_size()
        self.total_prefixes = 0
        self.total_passwords = 0

        logger.warning("Started.")
        self.session = connect(Path(self.options.db_path))
        self.updater = Updatinator(self.session)

    def configure_logging(self) -> None:
        """
        Log to a file in the same folder as the database file.
        """
        level = logging.INFO
        if self.options.verbose:
            level = logging.DEBUG
        if self.options.quiet:
            level = logging.WARNING

        path = Path(self.options.db_path).with_suffix('.log')
        handler = logging.FileHandler(filename=path)
        handler.setFormatter(Formatter())

        logging.basicConfig(
            format="%(message)s",
            handlers=(handler,),
            level=level,
        )

    def make_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Create and update database of passwords")
        parser.add_argument(
            'db_path', metavar='DB_PATH', help="path to password database",
        )

        # Logger verbosity
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '-q', '--quiet', action='store_true',
            help='log only warnings and errors',
        )
        group.add_argument(
            '-v', '--verbose', action='store_true',
            help='enable debug logging messages',
        )
        return parser

    def create_new(self) -> None:
        prefix, num_passwords = self.updater.create_new()
        logger.info(
            f"Prefix {prefix!r} and its {num_passwords} password hashes created."
        )
        self.total_prefixes += 1
        self.total_passwords += num_passwords
        self.print_progress(prefix)

    def print_progress(self, prefix: str) -> None:
        completed = self.updater.prefixes.percentage_complete()
        progress = f"{completed:.2f}% completed. Downloaded prefix {prefix}."
        print(progress, end="\r")

    def run(self) -> int:
        started = time.perf_counter()
        next_prefix = self.updater.prefixes.find_missing()
        start = f"Downloading new password hashes, starting with {next_prefix}"
        logger.info(start)
        print(start)

        while True:
            try:
                self.create_new()
            except SystemExit as e:
                self.session.close()
                logger.error(e)
                print()
                print(e, file=sys.stderr)
                break

        elapsed = time.perf_counter() - started
        duration = utils.duration(elapsed)
        summary = (
            f"Finished. Created {self.total_prefixes:,} prefix and "
            f"{self.total_passwords:,} password records in {duration}."
        )
        print(summary)
        logger.warning(summary)

        return 0
