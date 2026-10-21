import unittest

from Lib.jellyfin_auth import (
    requires_modern_auth,
    authorization_headers,
    request_headers,
    api_url,
)


class RequiresModernAuthTest(unittest.TestCase):
    def test_jellyfin_12_uses_modern_auth(self):
        self.assertTrue(requires_modern_auth('Jellyfin Server', '12.0.0'))

    def test_jellyfin_12_2_uses_modern_auth(self):
        self.assertTrue(requires_modern_auth('Jellyfin Server', '12.2.0'))

    def test_jellyfin_10_uses_legacy_auth(self):
        self.assertFalse(requires_modern_auth('Jellyfin Server', '10.11.0'))

    def test_emby_uses_legacy_auth(self):
        self.assertFalse(requires_modern_auth('Emby Server', '4.8.0.0'))

    def test_missing_product_uses_legacy_auth(self):
        self.assertFalse(requires_modern_auth(None, '12.0.0'))

    def test_missing_version_uses_legacy_auth(self):
        self.assertFalse(requires_modern_auth('Jellyfin Server', None))

    def test_unparsable_version_uses_legacy_auth(self):
        self.assertFalse(requires_modern_auth('Jellyfin Server', 'dev'))


class AuthorizationHeadersTest(unittest.TestCase):
    def test_media_browser_token_header(self):
        self.assertEqual(
            authorization_headers('abc123'),
            {'Authorization': 'MediaBrowser Token="abc123"'},
        )


class RequestHeadersTest(unittest.TestCase):
    def test_modern_auth_adds_token_header(self):
        self.assertEqual(
            request_headers('abc123', True),
            {'Authorization': 'MediaBrowser Token="abc123"'},
        )

    def test_legacy_auth_adds_no_token_header(self):
        self.assertEqual(request_headers('abc123', False), {})

    def test_extra_headers_are_preserved(self):
        self.assertEqual(
            request_headers('abc123', True, {'Content-Type': 'image/jpeg'}),
            {
                'Authorization': 'MediaBrowser Token="abc123"',
                'Content-Type': 'image/jpeg',
            },
        )


class ApiUrlTest(unittest.TestCase):
    def test_legacy_url_keeps_api_key_query(self):
        self.assertEqual(
            api_url('http://host/', 'Persons', 'abc123', False),
            'http://host/Persons?api_key=abc123',
        )

    def test_modern_url_omits_api_key_query(self):
        self.assertEqual(
            api_url('http://host/', 'Persons', 'abc123', True),
            'http://host/Persons',
        )


if __name__ == '__main__':
    unittest.main()
