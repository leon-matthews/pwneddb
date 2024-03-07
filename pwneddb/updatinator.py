"""
Update the database using the API.
"""

import logging
import time

from sqlalchemy.orm import Session

from .api import PwnedPasswordsAPIv3
from .db import Password, Prefix, PrefixManager


logger = logging.getLogger(__name__)


class Updatinator:
    """
    Coordinates between the API and DB classes to fetch and save records.

    There are two update phases:

    1. Initial download phase, where we keep choosing prefixes
       that we don't have yet.
    2. Update phase where we find an old prefix and update it.

    """
    def __init__(self, database_session: Session):
        self.prefixes = PrefixManager(database_session)
        self.api = PwnedPasswordsAPIv3()

    def create_new(self) -> tuple[str, int]:
        """
        Add a new prefix and its passwords.

        Returns:
            Prefix of newly created prefix and how many password hashes it had.
        """
        missing = self.prefixes.find_missing()
        if missing is None:
            message = "No missing prefixes found"
            logging.error(message)
            raise RuntimeError(message)

        logging.debug("Download missing prefix %r", missing)
        hashes = self.api.fetch_range(missing)
        passwords = []
        for sha1, count in hashes:
            passwords.append(Password(sha1=sha1, count=count))
        start = time.perf_counter()
        self.prefixes.add(Prefix(prefix=missing, passwords=passwords))
        logger.debug(
            f"Added {len(passwords):,} new passwords to database in "
            f"{time.perf_counter() - start:.3f}s"
        )
        return missing, len(passwords)

    def update_existing(self) -> None:
        """
        Update an already exsiting prefix and its passwords.

        * Will finding the oldest be too slow? Probably not, only four million
          prefixes.
        * Get feedback about how many hashes were actually updated. Should we
          abort update if no new data seems to be available?
        * Be careful not to lose existing plain-text passwords!
        * Update timestamp even if no hashes are updated.
        * Show average age of our records? Mean or median?
        """
