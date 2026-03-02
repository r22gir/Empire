"""
Email Alias and Inbox Management Service
Handles email aliases, forwarding, and unified inbox
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class EmailMessage:
    """Represents an email message"""
    id: str
    sender_name: str
    sender_email: str
    recipient: str
    subject: str
    body: str
    timestamp: datetime
    is_read: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class EmailAlias:
    """Represents an email alias"""
    username: str
    domain: str
    created_at: datetime
    is_active: bool = True
    
    @property
    def full_address(self) -> str:
        """Get full email address"""
        return f"{self.username}@{self.domain}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['full_address'] = self.full_address
        return data


class EmailService:
    """
    Email alias and inbox management service
    
    This service manages email aliases (username@marketforge.app) and provides
    unified inbox functionality. In production, this would integrate with:
    - Cloudflare Email Routing (or similar service) for email forwarding
    - Database for storing messages
    - SMTP service for sending emails
    """
    
    def __init__(self, domain: str = "marketforge.app"):
        """
        Initialize email service
        
        Args:
            domain: The domain for email aliases
        """
        self.domain = domain
        self.aliases: Dict[str, EmailAlias] = {}
        self.inbox: Dict[str, List[EmailMessage]] = {}
    
    def create_alias(self, username: str) -> EmailAlias:
        """
        Create a new email alias
        
        Args:
            username: Username for the alias
            
        Returns:
            Created EmailAlias object
            
        Raises:
            ValueError: If alias already exists
        """
        if username in self.aliases:
            raise ValueError(f"Alias {username}@{self.domain} already exists")
        
        alias = EmailAlias(
            username=username,
            domain=self.domain,
            created_at=datetime.now()
        )
        
        self.aliases[username] = alias
        self.inbox[username] = []
        
        # TODO: In production, integrate with Cloudflare Email Routing API
        # to actually create the email forwarding rule
        
        return alias
    
    def get_alias(self, username: str) -> Optional[EmailAlias]:
        """
        Get an email alias
        
        Args:
            username: Username to look up
            
        Returns:
            EmailAlias if found, None otherwise
        """
        return self.aliases.get(username)
    
    def delete_alias(self, username: str) -> bool:
        """
        Delete an email alias
        
        Args:
            username: Username to delete
            
        Returns:
            True if deleted, False if not found
        """
        if username not in self.aliases:
            return False
        
        self.aliases[username].is_active = False
        
        # TODO: In production, remove from Cloudflare Email Routing
        
        return True
    
    def get_inbox(self, username: str, unread_only: bool = False) -> List[EmailMessage]:
        """
        Get inbox messages for a user
        
        Args:
            username: Username to get inbox for
            unread_only: If True, only return unread messages
            
        Returns:
            List of EmailMessage objects
        """
        if username not in self.inbox:
            return []
        
        messages = self.inbox[username]
        
        if unread_only:
            messages = [msg for msg in messages if not msg.is_read]
        
        # Sort by timestamp, newest first
        return sorted(messages, key=lambda m: m.timestamp, reverse=True)
    
    def receive_email(self, username: str, sender_name: str, sender_email: str,
                     subject: str, body: str) -> EmailMessage:
        """
        Receive an incoming email (called by email webhook)
        
        Args:
            username: Recipient username
            sender_name: Sender's name
            sender_email: Sender's email address
            subject: Email subject
            body: Email body
            
        Returns:
            Created EmailMessage object
        """
        if username not in self.inbox:
            raise ValueError(f"No inbox found for {username}")
        
        message = EmailMessage(
            id=str(uuid.uuid4()),
            sender_name=sender_name,
            sender_email=sender_email,
            recipient=f"{username}@{self.domain}",
            subject=subject,
            body=body,
            timestamp=datetime.now(),
            is_read=False
        )
        
        self.inbox[username].append(message)
        
        return message
    
    def send_reply(self, username: str, recipient_email: str, subject: str,
                   body: str, in_reply_to: Optional[str] = None) -> bool:
        """
        Send an email reply from the alias
        
        Args:
            username: Username sending the reply
            recipient_email: Recipient's email address
            subject: Email subject
            body: Email body
            in_reply_to: Optional message ID this is replying to
            
        Returns:
            True if sent successfully
        """
        if username not in self.aliases:
            raise ValueError(f"Alias {username}@{self.domain} not found")
        
        alias = self.aliases[username]
        if not alias.is_active:
            raise ValueError(f"Alias {username}@{self.domain} is not active")
        
        # TODO: In production, integrate with SMTP service (SendGrid, AWS SES, etc.)
        # to actually send the email
        
        print(f"Sending email from {alias.full_address} to {recipient_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        
        return True
    
    def mark_as_read(self, username: str, message_id: str) -> bool:
        """
        Mark a message as read
        
        Args:
            username: Username
            message_id: Message ID
            
        Returns:
            True if marked, False if not found
        """
        if username not in self.inbox:
            return False
        
        for message in self.inbox[username]:
            if message.id == message_id:
                message.is_read = True
                return True
        
        return False
    
    def get_unread_count(self, username: str) -> int:
        """
        Get count of unread messages
        
        Args:
            username: Username
            
        Returns:
            Count of unread messages
        """
        if username not in self.inbox:
            return 0
        
        return sum(1 for msg in self.inbox[username] if not msg.is_read)


# Example usage
if __name__ == "__main__":
    service = EmailService()
    
    # Create alias
    print("Creating email alias...")
    alias = service.create_alias("john_doe")
    print(f"Created: {alias.full_address}")
    print()
    
    # Simulate receiving emails
    print("Simulating incoming emails...")
    service.receive_email(
        username="john_doe",
        sender_name="Jane Buyer",
        sender_email="jane@example.com",
        subject="Is this item still available?",
        body="Hi! I'm interested in the vintage lamp. Is it still available?"
    )
    
    service.receive_email(
        username="john_doe",
        sender_name="Bob Smith",
        sender_email="bob@example.com",
        subject="Question about shipping",
        body="Do you ship to Canada?"
    )
    print()
    
    # Get inbox
    print("Inbox:")
    messages = service.get_inbox("john_doe")
    for msg in messages:
        print(f"- [{msg.timestamp}] {msg.sender_name}: {msg.subject}")
    print()
    
    # Check unread count
    unread = service.get_unread_count("john_doe")
    print(f"Unread messages: {unread}")
    print()
    
    # Send reply
    print("Sending reply...")
    service.send_reply(
        username="john_doe",
        recipient_email="jane@example.com",
        subject="Re: Is this item still available?",
        body="Yes! It's still available. Ready to ship today!"
    )
