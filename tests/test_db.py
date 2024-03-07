
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from sqlalchemy import inspect, select
from sqlalchemy.engine.base import Engine as SQLAlchemyEngine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.session import Session as SQLAlchemySession

from pwneddb.db import connect, Password, Prefix

from .base import logger_hush, TransactionTestCase


def get_table_names(session: SQLAlchemySession) -> list[str]:
    assert isinstance(session.bind, SQLAlchemyEngine)
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()
    return tables


class ConnectTest(TestCase):
    temp_folder: TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_folder = TemporaryDirectory()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_folder.cleanup()

    def path_name(self, file_name: str) -> Path:
        """
        Build path inside test class's temporary folder.
        """
        path = Path(self.temp_folder.name) / file_name
        return path

    def test_connect_default(self) -> None:
        session = connect()
        assert isinstance(session, SQLAlchemySession)
        assert isinstance(session.bind, SQLAlchemyEngine)
        self.assertEqual(session.bind.url.drivername, 'sqlite+pysqlite')
        self.assertEqual(session.bind.url.database, ':memory:')

    def test_connect_create_file(self) -> None:
        path = self.path_name('passwords.db')

        # Suppress 'cretae new database' warning log message
        with logger_hush():
            session = connect(path)

        try:
            assert isinstance(session, SQLAlchemySession)
            assert isinstance(session.bind, SQLAlchemyEngine)
            self.assertEqual(session.bind.url.drivername, 'sqlite+pysqlite')
            assert session.bind.url.database is not None
            self.assertTrue(session.bind.url.database.endswith(path.name))
            self.assertEqual(get_table_names(session), ['passwords', 'prefixes'])
        finally:
            session.close()

    def test_connect_existing_file(self) -> None:
        # Create existing
        path = self.path_name('existing.db')
        path.touch()

        session = connect(path)
        try:
            assert isinstance(session, SQLAlchemySession)
            assert isinstance(session.bind, SQLAlchemyEngine)
            self.assertEqual(session.bind.url.drivername, 'sqlite+pysqlite')
            assert session.bind.url.database is not None
            self.assertTrue(session.bind.url.database.endswith(path.name))
            self.assertEqual(get_table_names(session), ['passwords', 'prefixes'])
        finally:
            session.close()


class PasswordTest(TransactionTestCase):
    """
    Test ``Password`` database model.
    """
    PASSWORD = {
        'sha1': "c8fed00eb2e87f1cee8e90ebbe870c190ac3848c",
        'password': "password",
        'count': 9_659_365,
        'prefix_id': 1,
    }

    def test_repr(self) -> None:
        password = Password(**self.PASSWORD)
        self.assertEqual(
            repr(password),
            "<Password: c8fed00eb2e87f1cee8e90ebbe870c190ac3848c ('password') 9,659,365>",
        )

    def test_add(self) -> None:
        # Prepare
        Prefix.objects(self.session).add(Prefix(prefix='abcde'))
        manager = Password.objects(self.session)
        password = Password(**self.PASSWORD)
        self.assertEqual(password.id, None)
        self.assertEqual(manager.count_rows(), 0)

        # Create
        self.session.add(password)
        self.session.commit()

        # Check state
        self.assertEqual(password.id, 1)
        self.assertEqual(manager.count_rows(), 1)
        self.assertEqual(
            repr(password),
            "<Password: c8fed00eb2e87f1cee8e90ebbe870c190ac3848c ('password') 9,659,365>",
        )


class PasswordManagerTest(TransactionTestCase):
    pass


class PrefixTest(TransactionTestCase):
    """
    Test ``Prefix`` database model.
    """
    def test_repr(self) -> None:
        prefix = Prefix(prefix='abcde', updated=1681081917.208)
        self.assertEqual(
            repr(prefix),
            "<Prefix: 'abcde' 2023-04-09T23:11:57Z>",
        )

    def test_repr_no_updated(self) -> None:
        prefix = Prefix(prefix='abcde')
        self.assertEqual(repr(prefix), "<Prefix: 'abcde'>")

    def test_add(self) -> None:
        manager = Prefix.objects(self.session)
        prefix = Prefix(
            prefix='abcde',
        )
        self.assertIsNone(prefix.id)
        self.assertIsNone(prefix.get_updated())
        self.assertEqual(manager.count_rows(), 0)

        self.session.add(prefix)
        self.session.commit()

        self.assertEqual(prefix.id, 1)
        self.assertIsInstance(prefix.get_updated(), datetime)
        self.assertEqual(manager.count_rows(), 1)

    def test_add_force_lowercase(self) -> None:
        manager = Prefix.objects(self.session)
        self.assertEqual(manager.count_rows(), 0)
        self.session.add_all([
            Prefix(prefix='ab001'),
            Prefix(prefix='aB002'),
            Prefix(prefix='Ab003'),
            Prefix(prefix='AB004'),
        ])
        self.assertEqual(manager.count_rows(), 4)

        prefixes = [prefix.prefix for prefix in self.session.scalars(select(Prefix))]
        expected = ['ab001', 'ab002', 'ab003', 'ab004']
        self.assertEqual(prefixes, expected)

    def test_add_not_unique(self) -> None:
        manager = Prefix.objects(self.session)
        self.assertEqual(manager.count_rows(), 0)
        self.session.add(Prefix(prefix='abcde'))
        self.session.add(Prefix(prefix='ABCDE'))
        message = r".*UNIQUE constraint failed: prefixes.prefix.*"
        with self.assertRaisesRegex(IntegrityError, message):
            self.session.commit()

    def test_add_too_long(self) -> None:
        message = r"^Given prefix not 5-characters long: 'abcdef'$"
        with self.assertRaisesRegex(ValueError, message):
            Prefix(prefix='abcdef')

    def test_add_too_short(self) -> None:
        message = r"^Given prefix not 5-characters long: 'abcd'$"
        with self.assertRaisesRegex(ValueError, message):
            Prefix(prefix='abcd')


class PrefixManagerTest(TransactionTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.manager = Prefix.objects(self.session)

    def test_find_missing(self) -> None:
        """
        One bigger than the largest
        """
        self.manager.add_all([
            Prefix(prefix='000af'),
            Prefix(prefix='000b1'),
            Prefix(prefix='000b0'),
            Prefix(prefix='000ae'),
        ])
        self.assertEqual(self.manager.find_missing(), '000b2')

    def test_find_missing_empty(self) -> None:
        """
        Empty database? The first missing is the first possible.
        """
        missing = self.manager.find_missing()
        self.assertEqual(missing, '00000')
        self.manager.add(Prefix(prefix=missing))

        missing = self.manager.find_missing()
        self.assertEqual(missing, '00001')

    def test_find_missing_full(self) -> None:
        """
        Largest already the last? Prefix table must be full, right? ;-)
        """
        self.manager.add(Prefix(prefix='ffffe'))
        missing = self.manager.find_missing()
        self.assertEqual(missing, 'fffff')

        self.manager.add(Prefix(prefix=missing))
        missing = self.manager.find_missing()
        self.assertEqual(missing, None)

    def test_largest_prefix(self) -> None:
        """The largest alphanumerically and arithmetically"""
        self.manager.add_all([
            Prefix(prefix='000af'),
            Prefix(prefix='000b1'),
            Prefix(prefix='000b0'),
            Prefix(prefix='000ae'),
        ])
        self.assertEqual(self.manager.largest_prefix(), '000b1')

    def test_largest_prefix_empty(self) -> None:
        """
        Empty database? None is largest
        """
        self.assertEqual(self.manager.largest_prefix(), None)

    def test_percent_completed_empty(self) -> None:
        self.assertEqual(self.manager.percentage_complete(), 0.0)

    def test_percent_completed_one(self) -> None:
        self.manager.add(Prefix(prefix='00000'))
        self.assertAlmostEqual(self.manager.percentage_complete(), (1 / 2**20) * 100)

    def test_percent_completed_full(self) -> None:
        self.manager.add(Prefix(prefix='fffff'))
        self.assertAlmostEqual(self.manager.percentage_complete(), 100)
