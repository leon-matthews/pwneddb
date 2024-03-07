
from unittest import mock, TestCase

from pwneddb.api import Prefix, PwnedPasswordsAPIv3

from .base import FakeResponse


class PrefixTest(TestCase):
    def test_create(self) -> None:
        self.assertEqual(str(Prefix('decaf')), 'decaf')
        self.assertEqual(str(Prefix('DECAF')), 'decaf')
        self.assertEqual(str(Prefix('0xdecaf')), 'decaf')
        self.assertEqual(str(Prefix('0XDECAF')), 'decaf')

    def test_create_wrong_length(self) -> None:
        message = r"^prefix must be exactly 5-characters long$"
        with self.assertRaisesRegex(ValueError, message):
            Prefix('abcdef')

    def test_create_not_hexadecimal(self) -> None:
        message = r"^prefix must be hexadecimal string$"
        with self.assertRaisesRegex(ValueError, message):
            Prefix('zyxwv')

    def test_equal(self) -> None:
        first = Prefix('1e240')
        second = Prefix.from_integer(123_456)
        self.assertEqual(first, second)

    def test_not_equal(self) -> None:
        first = Prefix('12345')
        self.assertFalse(first == 42)
        self.assertFalse(42 == first)
        self.assertFalse(first == '12345')
        self.assertFalse('12345' == first)

    def test_from_integer(self) -> None:
        self.assertEqual(Prefix.MAX_VALUE, 1_048_575)
        self.assertEqual(Prefix.from_integer(0), Prefix('00000'))
        self.assertEqual(Prefix.from_integer(123_456), Prefix('1e240'))
        self.assertEqual(Prefix.from_integer(1_048_575), Prefix('fffff'))

    def test_from_integer_negative(self) -> None:
        message = r"^value must be a positive integer$"
        with self.assertRaisesRegex(ValueError, message):
            Prefix.from_integer(-3)

    def test_from_integer_too_large(self) -> None:
        message = r"^value cannot be greater than MAX_VALUE$"
        with self.assertRaisesRegex(ValueError, message):
            Prefix.from_integer(2**20)

    def test_int(self) -> None:
        prefix = Prefix.from_integer(123_456)
        self.assertEqual(repr(prefix), '<Prefix: 1e240>')
        self.assertEqual(int(prefix), 123_456)

    def test_random(self) -> None:
        for _ in range(1_000):
            prefix = Prefix.random()
            self.assertIsInstance(prefix, Prefix)
            self.assertEqual(len(prefix), 5)

    def test_repr(self) -> None:
        prefix = Prefix.from_integer(721077)
        self.assertEqual(repr(prefix), '<Prefix: b00b5>')

    def test_str(self) -> None:
        prefix = Prefix.from_integer(721077)
        self.assertEqual(str(prefix), 'b00b5')


class PwnedPasswordsAPIv3Test(TestCase):
    downloader: PwnedPasswordsAPIv3

    BODY = (
        '003CD215739D7C1B2218670D26F81408237:1\r\n'
        '003D68EB55068C33ACE09247EE4C639306B:4\r\n'
        '012C192B2F16F82EA0EB9EF18D9D539B0DD:3\r\n'
        '01330C689E5D64F660D6947A93AD634EF8F:0\r\n'
    )
    BODY_BAD = (
        'The hash prefix was not in a valid format\r\n'
    )
    BODY_BAD2 = (
        '003CD215739D7C1B2218670D26F81408237:1\r\n'
        '003D68EB55068C33ACE09247EE4C639306B:4\r\n'
        '012C192B2F16F82EA0EB9EF18D9D539B0DD:null\r\n'
        '01330C689E5D64F660D6947A93AD634EF8F:0\r\n'
    )
    PREFIX = Prefix('5baa6')
    EXPECTED = [
        ('5baa6003cd215739d7c1b2218670d26f81408237', 1),
        ('5baa6003d68eb55068c33ace09247ee4c639306b', 4),
        ('5baa6012c192b2f16f82ea0eb9ef18d9d539b0dd', 3),
        ('5baa601330c689e5d64f660d6947a93ad634ef8f', 0),
    ]

    @classmethod
    def setUpClass(cls) -> None:
        cls.downloader = PwnedPasswordsAPIv3()

    def test_extract_expected_types(self) -> None:
        hashes = self.downloader._extract(self.PREFIX, self.BODY)

        for hash_, count in hashes:
            self.assertIsInstance(hash_, str)
            self.assertEqual(len(hash_), 40)
            self.assertIsInstance(count, int)

        self.assertEqual(hashes, self.EXPECTED)

    def test_extract_bad(self) -> None:
        message = r"^line 1: not enough values to unpack \(expected 2, got 1\)$"
        with self.assertRaisesRegex(RuntimeError, message):
            self.downloader._extract(self.PREFIX, self.BODY_BAD)

    def test_extract_bad2(self) -> None:
        message = r"^line 3: invalid literal for int\(\) with base 10: 'null'$"
        with self.assertRaisesRegex(RuntimeError, message):
            self.downloader._extract(self.PREFIX, self.BODY_BAD2)

    def test_fetch_range(self) -> None:
        """
        Run API call using mocked GET response.
        """
        prefix = self.PREFIX
        response = FakeResponse(text=self.BODY)
        with mock.patch.object(
            self.downloader.session, 'request', return_value=response,
        ):
            counts = self.downloader.fetch_range(prefix)
        self.assertEqual(counts, self.EXPECTED)

    def test_fetch_range_from_string(self) -> None:
        """
        Use plain-text (and upper-case) prefix in call to fetch_range().
        """
        prefix = '5BAA6'
        response = FakeResponse(text=self.BODY)
        with mock.patch.object(
            self.downloader.session, 'request', return_value=response,
        ):
            counts = self.downloader.fetch_range(prefix)
        self.assertEqual(counts, self.EXPECTED)
