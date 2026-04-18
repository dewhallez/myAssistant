import unittest
from unittest.mock import patch, MagicMock, mock_open
import datetime
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from main import get_credentials, get_daily_summary, _get_email_headers


class TestGetCredentials(unittest.TestCase):
    """Test credential retrieval and authentication."""

    @patch('main.os.path.exists')
    @patch('main.Credentials.from_authorized_user_file')
    def test_load_existing_token(self, mock_from_file, mock_exists):
        """Test loading existing credentials from token.json."""
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_file.return_value = mock_creds

        result = get_credentials()

        self.assertEqual(result, mock_creds)
        mock_exists.assert_called_once_with('token.json')
        mock_from_file.assert_called_once()

    @patch('main.os.path.exists')
    @patch('main.Credentials.from_authorized_user_file')
    @patch('main.Request')
    def test_refresh_expired_token(self, mock_request, mock_from_file, mock_exists):
        """Test refreshing expired credentials."""
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = True
        mock_creds.to_json.return_value = '{"type": "authorized_user"}'
        mock_from_file.return_value = mock_creds

        with patch('builtins.open', mock_open()):
            result = get_credentials()

        self.assertEqual(result, mock_creds)
        mock_creds.refresh.assert_called_once()

    @patch('main.os.path.exists')
    @patch('main.InstalledAppFlow.from_client_secrets_file')
    def test_new_oauth_flow(self, mock_flow, mock_exists):
        """Test initiating new OAuth flow."""
        mock_exists.return_value = False
        mock_flow_instance = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"type": "authorized_user"}'
        mock_flow_instance.run_local_server.return_value = mock_creds
        mock_flow.return_value = mock_flow_instance

        with patch('builtins.open', mock_open()):
            result = get_credentials()

        self.assertEqual(result, mock_creds)
        mock_flow.assert_called_once()

    @patch('main.os.path.exists')
    @patch('main.Credentials.from_authorized_user_file')
    def test_credentials_file_not_found(self, mock_from_file, mock_exists):
        """Test handling missing credentials file."""
        mock_exists.return_value = True
        mock_from_file.side_effect = FileNotFoundError("credentials.json not found")

        result = get_credentials()

        self.assertIsNone(result)

    @patch('main.os.path.exists')
    @patch('main.Credentials.from_authorized_user_file')
    def test_refresh_error(self, mock_from_file, mock_exists):
        """Test handling refresh errors."""
        mock_exists.return_value = True
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = True
        mock_creds.refresh.side_effect = RefreshError("Token refresh failed")
        mock_from_file.return_value = mock_creds

        result = get_credentials()

        self.assertIsNone(result)


class TestGetEmailHeaders(unittest.TestCase):
    """Test email header parsing."""

    def test_convert_headers_to_dict(self):
        """Test converting headers list to dictionary."""
        headers = [
            {'name': 'From', 'value': 'sender@example.com'},
            {'name': 'Subject', 'value': 'Test Email'},
            {'name': 'Date', 'value': '2026-04-18'}
        ]

        result = _get_email_headers(headers)

        self.assertEqual(result['From'], 'sender@example.com')
        self.assertEqual(result['Subject'], 'Test Email')
        self.assertEqual(result['Date'], '2026-04-18')

    def test_missing_header_value(self):
        """Test handling headers without values."""
        headers = [
            {'name': 'From'},
            {'name': 'Subject', 'value': 'Test'}
        ]

        result = _get_email_headers(headers)

        self.assertEqual(result['From'], '')
        self.assertEqual(result['Subject'], 'Test')

    def test_empty_headers(self):
        """Test handling empty headers list."""
        headers = []

        result = _get_email_headers(headers)

        self.assertEqual(result, {})


class TestGetDailySummary(unittest.TestCase):
    """Test daily summary generation."""

    @patch('main.get_credentials')
    def test_no_credentials(self, mock_get_creds):
        """Test handling when credentials are unavailable."""
        mock_get_creds.return_value = None

        # Should not raise exception
        result = get_daily_summary()

        self.assertIsNone(result)
        mock_get_creds.assert_called_once()

    @patch('main.get_credentials')
    @patch('main.build')
    def test_api_build_failure(self, mock_build, mock_get_creds):
        """Test handling API service initialization failure."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_build.side_effect = HttpError(
            MagicMock(status=401),
            b'Unauthorized'
        )

        # Should not raise exception
        result = get_daily_summary()

        self.assertIsNone(result)

    @patch('main.get_credentials')
    @patch('main.build')
    def test_calendar_events_success(self, mock_build, mock_get_creds):
        """Test successfully fetching calendar events."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        # Mock Gmail and Calendar services
        mock_gmail = MagicMock()
        mock_calendar = MagicMock()
        mock_build.side_effect = [mock_gmail, mock_calendar]

        # Mock calendar events - properly set up the chain
        mock_events = {
            'items': [
                {
                    'start': {'dateTime': '2026-04-18T14:00:00Z'},
                    'summary': 'Team Meeting'
                },
                {
                    'start': {'date': '2026-04-19'},
                    'summary': 'All-day Event'
                }
            ]
        }
        mock_calendar.events.return_value.list.return_value.execute.return_value = mock_events

        # Mock no emails
        mock_gmail.users.return_value.messages.return_value.list.return_value.execute.return_value = {'messages': []}

        # Should not raise exception
        result = get_daily_summary()

        self.assertIsNone(result)
        mock_calendar.events.return_value.list.assert_called_once()

    @patch('main.get_credentials')
    @patch('main.build')
    def test_email_fetching_with_errors(self, mock_build, mock_get_creds):
        """Test email fetching with partial failures."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_gmail = MagicMock()
        mock_calendar = MagicMock()
        mock_build.side_effect = [mock_gmail, mock_calendar]

        # Mock no calendar events
        mock_calendar.events().list().execute.return_value = {'items': []}

        # Mock emails with one error
        mock_messages = [
            {'id': '123'},
            {'id': '456'}
        ]
        mock_gmail.users().messages().list().execute.return_value = {
            'messages': mock_messages
        }

        # First email succeeds, second fails
        mock_get_call = mock_gmail.users().messages().get()
        mock_getitem_call = MagicMock()
        mock_getitem_call.execute.side_effect = [
            {
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': 'test@example.com'},
                        {'name': 'Subject', 'value': 'Test'}
                    ]
                },
                'snippet': 'Test message'
            },
            HttpError(MagicMock(status=404), b'Not Found')
        ]
        mock_getitem_call.return_value = MagicMock()
        mock_getitem_call.return_value.execute = mock_getitem_call.execute
        mock_get_call.return_value = MagicMock(
            execute=MagicMock(side_effect=[
                {
                    'payload': {
                        'headers': [
                            {'name': 'From', 'value': 'test@example.com'},
                            {'name': 'Subject', 'value': 'Test'}
                        ]
                    },
                    'snippet': 'Test message'
                },
                HttpError(MagicMock(status=404), b'Not Found')
            ])
        )
        mock_gmail.users().messages().get = MagicMock(
            return_value=mock_get_call
        )

        # Should not raise exception even with one email failing
        result = get_daily_summary()

        self.assertIsNone(result)

    @patch('main.get_credentials')
    @patch('main.build')
    def test_no_events_and_emails(self, mock_build, mock_get_creds):
        """Test handling when no events or emails are returned."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_gmail = MagicMock()
        mock_calendar = MagicMock()
        mock_build.side_effect = [mock_gmail, mock_calendar]

        # Mock empty results
        mock_calendar.events().list().execute.return_value = {'items': []}
        mock_gmail.users().messages().list().execute.return_value = {}

        result = get_daily_summary()

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
