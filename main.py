#Enable APIs: Go to the Google Cloud Console, create a project, and enable the Gmail API and Google Calendar API.

#Credentials: Create "OAuth Client ID" credentials (Desktop app) and download the credentials.json file to your project folder.#

import datetime
import logging
import os.path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
CALENDAR_ID = 'primary'
MAX_EMAILS = 5

def get_credentials() -> Optional[Credentials]:
    """
    Authenticate and return Google API credentials.
    Uses token.json if available, otherwise initiates OAuth flow.
    
    Returns:
        Credentials object or None if authentication fails.
    """
    creds = None
    try:
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("Loaded credentials from token.json")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                logger.info("Initiating OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            logger.info("Credentials saved to token.json")
        
        return creds
    except FileNotFoundError as e:
        logger.error(f"Credentials file not found: {e}")
        return None
    except RefreshError as e:
        logger.error(f"Failed to refresh credentials: {e}")
        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

def _get_email_headers(headers: list) -> dict:
    """Convert headers list to a dict for easier lookup."""
    return {h['name']: h.get('value', '') for h in headers}


def get_daily_summary() -> None:
    """
    Fetch and display a daily summary of calendar events and unread emails.
    """
    creds = get_credentials()
    if not creds:
        logger.error("Failed to obtain credentials. Exiting.")
        return

    try:
        # Initialize Services
        gmail = build('gmail', 'v1', credentials=creds)
        calendar = build('calendar', 'v3', credentials=creds)
        logger.info("Successfully connected to Gmail and Calendar APIs")
    except HttpError as e:
        logger.error(f"Failed to build API services: {e}")
        return

    logger.info(f"--- Daily Summary for {datetime.date.today()} ---")

    # 1. Fetch Calendar Events
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        end_of_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)).isoformat()
        
        events_result = calendar.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        logger.info("[Calendar Activity]")
        if not events:
            logger.info("No upcoming events for the next 24 hours.")
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', '(No title)')
                logger.info(f"- {start}: {summary}")
    except HttpError as e:
        logger.error(f"Failed to fetch calendar events: {e}")

    # 2. Fetch Unread Emails
    try:
        results = gmail.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=MAX_EMAILS
        ).execute()
        messages = results.get('messages', [])

        logger.info("[Important/Unread Emails]")
        if not messages:
            logger.info("No new unread emails.")
        else:
            for msg in messages:
                try:
                    txt = gmail.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    payload = txt.get('payload', {})
                    headers = payload.get('headers', [])
                    header_dict = _get_email_headers(headers)
                    
                    subject = header_dict.get('Subject', '(No subject)')
                    sender = header_dict.get('From', '(Unknown sender)')
                    
                    # Extract body snippet
                    snippet = txt.get('snippet', '(No preview available)')
                    
                    logger.info(f"- From: {sender}")
                    logger.info(f"  Subject: {subject}")
                    logger.info(f"  Preview: {snippet[:100]}...")
                except HttpError as e:
                    logger.warning(f"Failed to fetch message {msg['id']}: {e}")
                    continue
    except HttpError as e:
        logger.error(f"Failed to fetch emails: {e}")

if __name__ == '__main__':
    try:
        get_daily_summary()
        logger.info("Daily summary completed successfully")
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)