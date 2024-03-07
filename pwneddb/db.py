"""
Database interface via SQLAlchemy.

CREATE TABLE prefixes (
    id INTEGER NOT NULL,
    prefix VARCHAR(5) NOT NULL,
    updated FLOAT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (prefix)
);

CREATE TABLE passwords (
    id INTEGER NOT NULL,
    sha1 VARCHAR(40) NOT NULL,
    password VARCHAR,
    count INTEGER NOT NULL,
    prefix_id INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(prefix_id) REFERENCES prefixes (id)
);

"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Any, Iterable, Optional, Type

from sqlalchemy import create_engine, event, func, ForeignKey, select, String
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
    sessionmaker,
    validates,
)


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def connect(path: Optional[Path] = None) -> Session:
    """
    Create an SQLAlchemy session instance.
    """
    location = ":memory:"
    if path is not None:
        location = str(path)
        if path.exists():
            logger.debug("Connecting to existing SQLite3 database: %s", path)
        else:
            logger.warning("Creating new SQLite3 database: %s", path)

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        logger.debug("Running SQLite3 PRAGMAs")
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')
        cursor.execute('PRAGMA journal_mode = WAL;')
        cursor.execute('PRAGMA synchronous = NORMAL;')
        cursor.execute('PRAGMA temp_store = MEMORY;')
        cursor.execute('PRAGMA optimize;')
        cursor.close()

    uri = f"sqlite+pysqlite:///{location}"
    engine = create_engine(uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


class Manager:
    """
    Functions that operate on many rows, not just one.
    """
    model: Type[Base]

    def __init__(self, session: Session):
        self.session = session

    def add(self, instance: Base) -> None:
        self.session.add(instance)
        self.session.commit()

    def add_all(self, instances: Iterable[Base]) -> None:
        self.session.add_all(instances)
        self.session.commit()

    def count_rows(self) -> int:
        """
        Count total number of rows in table.
        """
        statement = select(func.count()).select_from(self.model)
        num_rows = self.session.scalars(statement).first()
        assert num_rows is not None
        return int(num_rows)


class Password(Base):
    __tablename__ = 'passwords'

    # Fields
    id: Mapped[int] = mapped_column(primary_key=True)
    sha1: Mapped[str] = mapped_column(String(40))
    password: Mapped[Optional[str]]
    count: Mapped[int]

    # Relationships
    prefix_id: Mapped[int] = mapped_column(ForeignKey("prefixes.id"))
    prefix: Mapped["Prefix"] = relationship(back_populates="passwords")

    def __repr__(self) -> str:
        password = "" if self.password is None else f" ({self.password!r})"
        return f"<{self.__class__.__name__}: {self.sha1}{password} {self.count:,}>"

    @staticmethod
    def objects(session: Session) -> PasswordManager:
        return PasswordManager(session)


class PasswordManager(Manager):
    """
    Functions involving multiple Prefix models.
    """
    model = Password


class Prefix(Base):
    """

    # Create UTC timestamp
    updated = time.time()

    # Create correct datetime object from timestamp:
    d = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

    """
    __tablename__ = 'prefixes'

    # Fields
    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(5), unique=True)
    updated: Mapped[float] = mapped_column(default=time.time)

    # Relationships
    passwords: Mapped[list["Password"]] = relationship(
        back_populates="prefix", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        updated = self.get_updated()
        when_updated = ''
        if updated is not None:
            when_updated = updated.strftime('%Y-%m-%dT%H:%M:%SZ')
            when_updated = f" {when_updated}"
        return f"<{self.__class__.__name__}: {self.prefix!r}{when_updated}>"

    @staticmethod
    def objects(session: Session) -> PrefixManager:
        return PrefixManager(session)

    @validates('prefix')
    def validate_prefix(self, key: str, prefix: str) -> str:
        if len(prefix) != 5:
            raise ValueError(f"Given prefix not 5-characters long: {prefix!r}")
        prefix = prefix.casefold()
        return prefix

    def get_updated(self) -> datetime | None:
        """
        Get the timezone-aware, UTC datetime when prefix record was last updated.
        """
        updated = None
        if self.updated is not None:
            updated = datetime.fromtimestamp(self.updated, tz=timezone.utc)
        return updated


class PrefixManager(Manager):
    """
    Functions involving multiple Prefix models.
    """
    model = Prefix
    TOTAL_ROWS = 16**5                  # Five hexadecimal characters

    def find_missing(self) -> Optional[str]:
        """
        Return a prefix for a record we don't yet have.

        Currently finds the largest prefix and increases it numerically by one.
        Obviously, this will only work if we are very careful to only add
        records one at a time and in order.

        More robust would be to create all million or so possible prefix records
        with an `updated` value of NULL when setting up a new database, then
        simply select for NULL against our prefixes table.

        Given that we've already decided to be polite, and not to hammer the API
        with a hundred multithreaded requests at a time, this implementation
        will suffice.

        Returns:
            Prefix for a missing record, or None if no missing prefixes found.
        """
        largest = self.largest_prefix()

        # Empty table?
        if largest is None:
            return '00000'
        value = int(largest, 16) + 1

        # Full table?
        if value == self.TOTAL_ROWS:
            return None

        prefix = f"{value:0>5x}"
        return prefix

    def largest_prefix(self) -> Optional[str]:
        """
        Find the largest prefix value in the database.

        Returns:
            Largest prefix, or None if there are no prefixes to be had.
        """
        statement = select(self.model.prefix).order_by(self.model.prefix.desc())
        result = self.session.execute(statement).first()
        if result is None:
            return None
        prefix = result[0]
        assert isinstance(prefix, str)
        return prefix

    def percentage_complete(self) -> float:
        """
        Fetch percentage of possible prefixes that we have.

        We take advantage of the fact that we download our prefixes in strict
        numerical order to avoid the expensive full-table scan that SQLite
        always uses for a COUNT(*) query.
        """
        largest = self.largest_prefix()
        rows = 0
        if largest is not None:
            rows = int(largest, 16) + 1
        percentage = (rows / self.TOTAL_ROWS) * 100.0
        return percentage
