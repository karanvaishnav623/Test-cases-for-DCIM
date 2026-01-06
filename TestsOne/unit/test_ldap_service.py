
import unittest
import sys
from unittest.mock import MagicMock, patch, ANY

# Mock missing dependencies
sys.modules['pythonjsonlogger'] = MagicMock()
sys.modules['pythonjsonlogger.jsonlogger'] = MagicMock()

# Mock app.core.logger before importing service that uses it
mock_logger_module = MagicMock()
sys.modules['app.core.logger'] = mock_logger_module
mock_logger_module.app_logger = MagicMock()

# Mock ldap3 dependencies
mock_ldap3 = MagicMock()
sys.modules['ldap3'] = mock_ldap3
sys.modules['ldap3.core'] = MagicMock()
sys.modules['ldap3.core.exceptions'] = MagicMock()

# Define a real Exception class for LDAPException so it can be caught
class MockLDAPException(Exception):
    pass

sys.modules['ldap3.core.exceptions'].LDAPException = MockLDAPException

from app.services.ldap_service import ldap_authenticate
from ldap3.core.exceptions import LDAPException

# Mock data
SERVER_URI = "ldap://test.com"
BASE_DN = "dc=test,dc=com"
USERNAME = "jdoe"
PASSWORD = "secretpassword"
BIND_DN = "cn=service,dc=test,dc=com"
BIND_PASSWORD = "servicepassword"

class TestLdapService(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        self.mock_ldap3 = sys.modules['ldap3']
        self.mock_ldap3.reset_mock()
        self.mock_server_cls = self.mock_ldap3.Server
        self.mock_connection_cls = self.mock_ldap3.Connection

    def test_ldap_authenticate_success(self):
        """
        Test successful authentication.
        """
        # Setup mocks
        mock_service_conn = MagicMock()
        mock_user_conn = MagicMock()
        
        # Side effect for Connection constructor
        self.mock_connection_cls.side_effect = [mock_service_conn, mock_user_conn]
        
        # Search behavior
        mock_entry = MagicMock()
        mock_entry.entry_dn = "cn=jdoe,dc=test,dc=com"
        mock_service_conn.entries = [mock_entry]
        
        # Bind behavior
        mock_user_conn.bind.return_value = True

        # Call function
        success, dn = ldap_authenticate(
            SERVER_URI, BASE_DN, USERNAME, PASSWORD, BIND_DN, BIND_PASSWORD
        )

        # Assertions
        self.assertTrue(success)
        self.assertEqual(dn, "cn=jdoe,dc=test,dc=com")
        
        # Verify Service Bind
        self.mock_connection_cls.assert_any_call(
            ANY, user=BIND_DN, password=BIND_PASSWORD, authentication=ANY, auto_bind=True
        )
        
        # Verify Search
        mock_service_conn.search.assert_called_with(
            search_base=BASE_DN,
            search_filter=f"(sAMAccountName={USERNAME})",
            attributes=["distinguishedName"]
        )
        
        # Verify User Bind
        self.mock_connection_cls.assert_any_call(
            ANY, user="cn=jdoe,dc=test,dc=com", password=PASSWORD, authentication=ANY
        )
        mock_user_conn.bind.assert_called_once()


    def test_ldap_authenticate_user_not_found(self):
        """
        Test user not found scenario.
        """
        mock_service_conn = MagicMock()
        self.mock_connection_cls.side_effect = None
        self.mock_connection_cls.return_value = mock_service_conn
        
        # Search finds nothing
        mock_service_conn.entries = []

        success, dn = ldap_authenticate(
            SERVER_URI, BASE_DN, USERNAME, PASSWORD, BIND_DN, BIND_PASSWORD
        )

        self.assertFalse(success)
        self.assertIsNone(dn)
        
        mock_service_conn.search.assert_called_once()
        # Should not attempt user bind
        self.assertEqual(self.mock_connection_cls.call_count, 1)


    def test_ldap_authenticate_wrong_password(self):
        """
        Test wrong password scenario.
        """
        mock_service_conn = MagicMock()
        mock_user_conn = MagicMock()
        self.mock_connection_cls.side_effect = [mock_service_conn, mock_user_conn]
        
        # Search finds user
        mock_entry = MagicMock()
        mock_entry.entry_dn = "cn=jdoe,dc=test,dc=com"
        mock_service_conn.entries = [mock_entry]
        
        # User bind fails
        mock_user_conn.bind.return_value = False

        success, dn = ldap_authenticate(
            SERVER_URI, BASE_DN, USERNAME, PASSWORD, BIND_DN, BIND_PASSWORD
        )

        self.assertFalse(success)
        self.assertIsNone(dn)
        
        mock_user_conn.bind.assert_called_once()


    def test_ldap_authenticate_exception(self):
        """
        Test LDAP exception handling.
        """
        # Verify that it catches LDAPException
        self.mock_connection_cls.side_effect = LDAPException("Connection failed")

        success, dn = ldap_authenticate(
            SERVER_URI, BASE_DN, USERNAME, PASSWORD, BIND_DN, BIND_PASSWORD
        )

        self.assertFalse(success)
        self.assertIsNone(dn)

if __name__ == '__main__':
    unittest.main()
