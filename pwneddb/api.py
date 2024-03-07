"""
Fetch SHA-1 password hashes from the pwnedpasswords.com API.
"""

import logging
import random
import time
from types import NotImplementedType
from typing import TypeAlias

import requests


HashCounts: TypeAlias = list[tuple[str, int]]
logger = logging.getLogger(__name__)


class Prefix:
    """
    Five-character hex (20-bit) prefix to pass to API as range parameter.

    TODO:
        Figure out to do about conflict between this and the `db.Prefix` class.
        This was written first to abstract away operationial details, before
        the database layer was written.
    """
    MAX_VALUE = 16**5 - 1               # Five hexadecimal characters, plus zero

    def __init__(self, prefix: str):
        # Clean
        prefix = prefix.casefold()
        if prefix.startswith('0x'):
            prefix = prefix[2:]

        # Length?
        if len(prefix) != 5:
            raise ValueError('prefix must be exactly 5-characters long')

        # Hexadecimal?
        try:
            int(prefix, 16)
        except ValueError:
            raise ValueError('prefix must be hexadecimal string') from None

        self._prefix = prefix

    def __eq__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, Prefix):
            return NotImplemented
        return self._prefix == other._prefix

    def __int__(self) -> int:
        return int(self._prefix, 16)

    def __len__(self) -> int:
        return len(self._prefix)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self}>"

    def __str__(self) -> str:
        return self._prefix

    @classmethod
    def from_integer(cls, value: int) -> 'Prefix':
        value = int(value)
        if value < 0:
            raise ValueError('value must be a positive integer')
        if value > Prefix.MAX_VALUE:
            raise ValueError('value cannot be greater than MAX_VALUE')
        return cls(f"{value:0>5x}")

    @staticmethod
    def random() -> 'Prefix':
        value = random.randint(0, Prefix.MAX_VALUE)
        return Prefix.from_integer(value)


class PwnedPasswordsAPIv3:
    """
    Download password hashes from Pwned Passwords API v3.

    See:
        https://haveibeenpwned.com/
    """
    URL_RANGE = 'https://api.pwnedpasswords.com/range'

    def __init__(self, *, timeout: float = 5.0):
        """
        Initialiser.

        Args:
            timeout:
                Optionally override the number of seconds we'll wait for a
                server to respond before abandoning request.
        """
        # Core fields
        self.session = requests.session()
        self.timeout = timeout

        # Accounting. Bytes counts request/response body data only.
        self.bytes_received = 0
        self.num_requests = 0
        self.num_request_errors = 0

    def fetch_range(self, prefix: Prefix | str) -> HashCounts:
        """
        Fetch password hashes and their counts.

        Args:
            prefix:
                Five-character hexadecimal prefix.

        Returns:
            List of 2-tuples, each containing hash then count.
        """
        if not isinstance(prefix, Prefix):
            prefix = Prefix(prefix)
        url = f"{self.URL_RANGE}/{prefix}"
        string = self._get(url)
        data = self._extract(prefix, string)
        return data

    def _extract(self, prefix: Prefix, string: str) -> HashCounts:
        """
        Args:
            prefix:
                Five-character hexadecimal prefix.
            string:
                Multiline string from API.

        Returns:
            List of 2-tuples, hash string and integer counts.
        """
        data: HashCounts = []
        for number, line in enumerate(string.split(), 1):
            try:
                suffix, count = line.split(':')
                sha1sum = f"{prefix}{suffix}".casefold()
                datum = (sha1sum, int(count))
                data.append(datum)
            except ValueError as e:
                raise RuntimeError(f"line {number}: {e}") from None
        return data

    def _get(self, url: str) -> str:
        """
        Fetch hash prefixes and their counts from API endpoint.

        Args:
            url:
                Full URL to API endpoint.

        Returns:
            Plain-text, multliline string
        """
        # Request
        self.num_requests += 1
        start = time.perf_counter()
        response = self.session.get(url)
        response.raise_for_status()

        # Log result
        self.bytes_received += len(response.content)
        logger.debug(
            f"Fetched {len(response.content):,} bytes in "
            f"{time.perf_counter() - start:.3f}s from {url}"
        )
        return response.text
