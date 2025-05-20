import os
import base64
import mysql.connector
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Step 1: Gmail API Setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
creds = None

if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('gmail', 'v1', credentials=creds)

# Step 2: Search Emails
query = 'after:2025/05/09 before:2025/05/11'
  # Change this to your needs
results = service.users().messages().list(userId='me', q=query).execute()
messages = results.get('messages', [])

print(f"Found {len(messages)} emails.")

# Step 3: Connect to MySQL
db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='teja',  # change this!
    database='gmail_data'  # must create this first
)
cursor = db.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sender VARCHAR(255),
        subject TEXT,
        email_date VARCHAR(255),
        body LONGTEXT
    )
""")

# Step 4: Process and Store Emails
for msg in messages:
    msg_id = msg['id']
    msg_data = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
    raw_bytes = base64.urlsafe_b64decode(msg_data['raw'].encode('ASCII'))
    mime_msg = message_from_bytes(raw_bytes)

    sender = mime_msg.get('From')
    subject = mime_msg.get('Subject')
    date = mime_msg.get('Date')

    body = ''
    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(part.get("Content-Disposition")):
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = mime_msg.get_payload(decode=True).decode('utf-8', errors='ignore')

    # Insert into MySQL
    cursor.execute("INSERT INTO emails (sender, subject, email_date, body) VALUES (%s, %s, %s, %s)",
                   (sender, subject, date, body))
    db.commit()

print("✅ Done! Emails saved to database.")

