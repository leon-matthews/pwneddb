
from contextlib import contextmanager
import logging
from typing import Any, Iterator, Optional, TypeAlias, Union
from unittest import TestCase

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, NestedTransaction, Engine
from sqlalchemy.orm import Session

from pwneddb.db import Base


JSON: TypeAlias = Union[dict[str, Any], list[Any]]


class FakeResponse:
    """
    Fakes the interface of `requests.Response`.

    Use as the return value for mocked calls, eg.

        return_value = FakeRequestResponse(json={})

        with mock.patch.object(
            client.session, 'get', return_value=return_value) as mocked:
                response = client.get('/some/path')

        self.assertEqual(response.json(), {})
    """
    def __init__(
        self,
        *,
        content: Optional[bytes] = None,
        json: Optional[JSON] = None,
        text: Optional[str] = None,
    ):
        """
        Initialiser.

        Args:
            content:
                Byte string to use as `response.content` property.
            json:
                Dictionary or list to return from `response.json()` method.
            text:
                String to use as `response.text` property.
        """
        self._content = b'' if content is None else content
        self._json = {} if json is None else json
        self._text = '' if text is None else text

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        return self._text

    def raise_for_status(self) -> None:
        pass


@contextmanager
def logger_hush(level: int = logging.ERROR) -> Iterator[None]:
    """
    Context manager to disable logging at or below the given level.

            with logger_hush():
                noisy_operation()

    Especially useful when writing unittests. Although in that case, you may
    want to try the `CaptureLogs` context manager to test logging messages.
    """
    logging.disable(level)
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)


class TransactionTestCase(TestCase):
    """
    Efficient test isolation for unit tests using SQLAlchemy's ORM interface.

    Each test method is wrapped in its own transaction - writes to the database
    in any one function do not affect any other function.

    For efficiency's sake, the database connection and its tables are
    created only one per test class.
    """
    engine: Engine
    session: Session
    transaction: NestedTransaction

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine('sqlite+pysqlite:///:memory:')
        Base.metadata.create_all(cls.engine)

        # Enable nested transactions for SQLite, see:
        # https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#pysqlite-serializable
        @event.listens_for(cls.engine, "connect")
        def do_connect(dbapi_connection: Any, connection_record: Any) -> None:
            dbapi_connection.isolation_level = None             # pragma: nocover

        @event.listens_for(cls.engine, "begin")
        def do_begin(conn: Connection) -> None:
            conn.exec_driver_sql("BEGIN")

    def setUp(self) -> None:
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin_nested()
        self.session = Session(bind=self.connection)

    def tearDown(self) -> None:
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(cls.engine)
