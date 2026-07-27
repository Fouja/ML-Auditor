"""
Generic IMAP/SMTP email client.
Works with any email provider (Gmail, Outlook, Yahoo, custom, etc.).
"""

import email as email_lib
import imaplib
import logging
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Common provider presets
PROVIDERS = {
    "gmail": {
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "use_ssl": True,
    },
    "outlook": {
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "use_ssl": True,
    },
    "yahoo": {
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "use_ssl": True,
    },
    "custom": {
        "imap_host": "",
        "imap_port": 993,
        "smtp_host": "",
        "smtp_port": 587,
        "use_ssl": True,
    },
}


def _decode_header_value(raw: str) -> str:
    """Decode email header value (handles encoded words)."""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _parse_email(msg: email_lib.message.Message) -> Dict[str, Any]:
    """Parse an email message into a dict."""
    subject = _decode_header_value(msg.get("Subject", ""))
    sender = _decode_header_value(msg.get("From", ""))
    to = _decode_header_value(msg.get("To", ""))
    date_str = msg.get("Date", "")
    message_id = msg.get("Message-ID", "")
    in_reply_to = msg.get("In-Reply-To", "")

    body_text = ""
    body_html = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()

            if filename:
                attachments.append(
                    {
                        "filename": _decode_header_value(filename),
                        "content_type": content_type,
                        "size": len(part.get_payload(decode=True) or b""),
                    }
                )
            elif (
                content_type == "text/plain" and "attachment" not in content_disposition
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_text += payload.decode(charset, errors="replace")
            elif (
                content_type == "text/html" and "attachment" not in content_disposition
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_html += payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                body_html = text
            else:
                body_text = text

    return {
        "subject": subject,
        "from": sender,
        "to": to,
        "date": date_str,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
        "snippet": body_text[:200].strip() if body_text else "",
    }


class EmailClient:
    """
    Generic email client using IMAP (read) and SMTP (send).
    Supports any provider via presets or custom config.
    """

    def __init__(
        self,
        email_address: str,
        password: str,
        provider: str = "custom",
        imap_host: Optional[str] = None,
        imap_port: Optional[int] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        use_ssl: bool = True,
    ):
        self.email_address = email_address
        self.password = password
        preset = PROVIDERS.get(provider, PROVIDERS["custom"])

        self.imap_host = imap_host or preset["imap_host"]
        self.imap_port = imap_port or preset["imap_port"]
        self.smtp_host = smtp_host or preset["smtp_host"]
        self.smtp_port = smtp_port or preset["smtp_port"]
        self.use_ssl = use_ssl
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server."""
        if self._imap:
            try:
                self._imap.noop()
                return self._imap
            except Exception:
                self._imap = None

        self._imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        self._imap.login(self.email_address, self.password)
        logger.info(f"Connected to IMAP: {self.imap_host}")
        return self._imap

    def _disconnect_imap(self):
        """Disconnect from IMAP."""
        if self._imap:
            try:
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

    def list_folders(self) -> List[str]:
        """List available mail folders."""
        conn = self._connect_imap()
        status, folders = conn.list()
        result = []
        for f in folders:
            if isinstance(f, bytes):
                name = f.decode().split('" "')[-1].strip('"')
                result.append(name)
        return result

    def get_folders(self) -> List[Dict[str, Any]]:
        """Get folders with unread counts."""
        conn = self._connect_imap()
        status, folder_data = conn.list()
        result = []
        for f in folder_data:
            if isinstance(f, bytes):
                parts = f.decode()
                name = parts.split('" "')[-1].strip('"')
                try:
                    status, _ = conn.select(f'"{name}"', readonly=True)
                    if status == "OK":
                        _, msg_nums = conn.search(None, "UNSEEN")
                        unread = len(msg_nums[0].split()) if msg_nums[0] else 0
                        _, msg_nums_all = conn.search(None, "ALL")
                        total = len(msg_nums_all[0].split()) if msg_nums_all[0] else 0
                        result.append({"name": name, "unread": unread, "total": total})
                except Exception:
                    result.append({"name": name, "unread": 0, "total": 0})
        return result

    def get_messages(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        unread_only: bool = False,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a folder.

        Args:
            folder: Mail folder name
            limit: Max messages to return
            unread_only: Only return unread messages
            search: IMAP search filter (e.g. 'SINCE 01-Jan-2026')
        """
        conn = self._connect_imap()
        status, _ = conn.select(f'"{folder}"', readonly=True)
        if status != "OK":
            logger.warning(f"Could not select folder: {folder}")
            return []

        if unread_only:
            criteria = "UNSEEN"
        elif search:
            criteria = search
        else:
            criteria = "ALL"

        status, msg_nums = conn.search(None, criteria)
        if status != "OK" or not msg_nums[0]:
            return []

        ids = msg_nums[0].split()
        ids = ids[-limit:]  # Get latest
        ids.reverse()

        messages = []
        for mid in ids:
            status, msg_data = conn.fetch(mid, "(RFC822)")
            if status == "OK":
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                parsed = _parse_email(msg)
                uid = mid.decode()
                parsed["uid"] = uid
                parsed["id"] = uid
                parsed["folder"] = folder
                messages.append(parsed)

        return messages

    def get_message_by_id(
        self, uid: str, folder: str = "INBOX"
    ) -> Optional[Dict[str, Any]]:
        """Get a single message by UID."""
        conn = self._connect_imap()
        conn.select(f'"{folder}"', readonly=True)
        status, msg_data = conn.fetch(uid.encode(), "(RFC822)")
        if status == "OK" and msg_data[0]:
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            parsed = _parse_email(msg)
            parsed["uid"] = uid
            parsed["id"] = uid
            parsed["folder"] = folder
            return parsed
        return None

    def mark_as_read(self, uid: str, folder: str = "INBOX"):
        """Mark a message as read."""
        conn = self._connect_imap()
        conn.select(f'"{folder}"')
        conn.store(uid.encode(), "+FLAGS", "\\Seen")

    def mark_as_unread(self, uid: str, folder: str = "INBOX"):
        """Mark a message as unread."""
        conn = self._connect_imap()
        conn.select(f'"{folder}"')
        conn.store(uid.encode(), "-FLAGS", "\\Seen")

    def move_message(self, uid: str, from_folder: str, to_folder: str):
        """Move a message between folders."""
        conn = self._connect_imap()
        conn.select(f'"{from_folder}"')
        conn.copy(uid.encode(), f'"{to_folder}"')
        conn.store(uid.encode(), "+FLAGS", "\\Deleted")
        conn.expunge()

    def delete_message(self, uid: str, folder: str = "INBOX"):
        """Delete a message."""
        conn = self._connect_imap()
        conn.select(f'"{folder}"')
        conn.store(uid.encode(), "+FLAGS", "\\Deleted")
        conn.expunge()

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html: bool = False,
    ) -> bool:
        """
        Send an email via SMTP.

        Args:
            to: Recipient address
            subject: Email subject
            body: Email body
            cc: CC addresses
            bcc: BCC addresses
            html: Whether body is HTML
        """
        msg = MIMEMultipart()
        msg["From"] = self.email_address
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        recipients = [to]
        if cc:
            recipients.extend([a.strip() for a in cc.split(",")])
        if bcc:
            recipients.extend([a.strip() for a in bcc.split(",")])

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()

            server.login(self.email_address, self.password)
            server.sendmail(self.email_address, recipients, msg.as_string())
            server.quit()
            logger.info(f"Email sent to {to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def search_messages(
        self,
        query: str,
        folder: str = "INBOX",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for messages using IMAP search."""
        return self.get_messages(folder=folder, limit=limit, search=query)

    def test_connection(self) -> Dict[str, Any]:
        """Test IMAP connection."""
        try:
            conn = self._connect_imap()
            status, greeting = conn.welcome if hasattr(conn, "welcome") else ("OK", "")
            folders = self.list_folders()
            return {
                "success": True,
                "host": self.imap_host,
                "folders_count": len(folders),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self._disconnect_imap()
