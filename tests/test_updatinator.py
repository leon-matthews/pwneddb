
from unittest import mock, TestCase

from sqlalchemy.orm.session import Session as SQLAlchemySession

from pwneddb import db, updatinator

from .base import FakeResponse, logger_hush


RESPONSE = (
    '003CD215739D7C1B2218670D26F81408237:1\r\n'
    '003D68EB55068C33ACE09247EE4C639306B:4\r\n'
    '012C192B2F16F82EA0EB9EF18D9D539B0DD:3\r\n'
    '01330C689E5D64F660D6947A93AD634EF8F:0\r\n'
)


def count_records(session: SQLAlchemySession) -> tuple[int, int]:
    num_prefixes = db.PrefixManager(session).count_rows()
    num_passwords = db.PasswordManager(session).count_rows()
    return (num_prefixes, num_passwords)


class UpdatinatorTest(TestCase):
    updater: updatinator.Updatinator

    def setUp(self) -> None:
        self.session = db.connect()
        self.updater = updatinator.Updatinator(self.session)

    def test_create_new(self) -> None:
        self.assertEqual(count_records(self.session), (0, 0))

        response = FakeResponse(text=RESPONSE)
        with mock.patch.object(
            self.updater.api.session, 'request', return_value=response,
        ):
            self.updater.create_new()

        self.assertEqual(count_records(self.session), (1, 4))

    def test_create_new_full(self) -> None:
        self.session.add(db.Prefix(prefix='fffff'))
        message = r"^No missing prefixes found$"
        with self.assertRaisesRegex(RuntimeError, message), logger_hush():
            self.updater.create_new()
