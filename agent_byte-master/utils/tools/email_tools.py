"""
Email tools.

Relocated from empire/superagi's email tool suite.
Provides SMTP send and IMAP read without ORM dependencies.
"""

import email
import imaplib
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from frameworks.agents.tools import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SendEmailTool(BaseTool):
    """Send email via SMTP or save as draft via IMAP.

    Config keys: EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_SMTP_HOST,
                 EMAIL_SMTP_PORT, EMAIL_SIGNATURE, EMAIL_DRAFT_MODE
    """

    name = "send_email"
    description = "Send an email to a recipient with a subject and body."

    def _execute(self, to: str, subject: str, body: str, **kwargs) -> ToolResult:
        address = self.get_config("EMAIL_ADDRESS")
        password = self.get_config("EMAIL_PASSWORD")
        smtp_host = self.get_config("EMAIL_SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(self.get_config("EMAIL_SMTP_PORT", "587"))
        signature = self.get_config("EMAIL_SIGNATURE", "")
        draft_mode = self.get_config("EMAIL_DRAFT_MODE", "false").lower() == "true"

        if not address or not password:
            return ToolResult(output="EMAIL_ADDRESS and EMAIL_PASSWORD are required.", success=False)

        if signature:
            body += f"\n\n{signature}"

        msg = MIMEMultipart()
        msg["From"] = address
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if draft_mode:
            return self._save_draft(address, password, smtp_host, msg)

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(address, password)
                server.sendmail(address, to, msg.as_string())
            return ToolResult(output=f"Email sent to {to}.", metadata={"to": to, "subject": subject})
        except Exception as e:
            return ToolResult(output=f"Failed to send email: {e}", success=False)

    def _save_draft(self, address, password, host, msg) -> ToolResult:
        imap_host = host.replace("smtp.", "imap.")
        try:
            with imaplib.IMAP4_SSL(imap_host) as imap:
                imap.login(address, password)
                imap.append("[Gmail]/Drafts", "\\Draft", None, msg.as_bytes())
            return ToolResult(output="Email saved as draft.")
        except Exception as e:
            return ToolResult(output=f"Failed to save draft: {e}", success=False)

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        }


class ReadEmailTool(BaseTool):
    """Read emails from an IMAP mailbox.

    Config keys: EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_HOST
    """

    name = "read_email"
    description = "Read recent emails from a mailbox."

    def __init__(self, max_emails: int = 5, config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.max_emails = max_emails

    def _execute(self, folder: str = "INBOX", **kwargs) -> ToolResult:
        address = self.get_config("EMAIL_ADDRESS")
        password = self.get_config("EMAIL_PASSWORD")
        imap_host = self.get_config("EMAIL_IMAP_HOST", "imap.gmail.com")

        if not address or not password:
            return ToolResult(output="EMAIL_ADDRESS and EMAIL_PASSWORD are required.", success=False)

        try:
            with imaplib.IMAP4_SSL(imap_host) as imap:
                imap.login(address, password)
                imap.select(folder, readonly=True)
                _, message_numbers = imap.search(None, "ALL")
                ids = message_numbers[0].split()

                emails = []
                for msg_id in ids[-self.max_emails:]:
                    _, data = imap.fetch(msg_id, "(RFC822)")
                    raw = data[0][1]
                    msg = email.message_from_bytes(raw)

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="replace")

                    emails.append(
                        f"From: {msg['From']}\n"
                        f"Subject: {msg['Subject']}\n"
                        f"Date: {msg['Date']}\n"
                        f"{body[:500]}\n"
                    )

                if not emails:
                    return ToolResult(output="No emails found.")

                return ToolResult(
                    output="\n---\n".join(emails),
                    metadata={"count": len(emails), "folder": folder},
                )
        except Exception as e:
            return ToolResult(output=f"Failed to read emails: {e}", success=False)

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "IMAP folder (default: INBOX)"},
            },
            "required": [],
        }
