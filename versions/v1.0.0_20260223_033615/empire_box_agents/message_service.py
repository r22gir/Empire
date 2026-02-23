"""
Unified Message Service
Aggregates messages from multiple sources and generates AI responses
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from .request_router import RequestRouter
    from .email_service import EmailService, EmailMessage
except ImportError:
    # For running as standalone script
    from request_router import RequestRouter
    from email_service import EmailService, EmailMessage


class MessageSource(Enum):
    """Message source types"""
    EMAIL = "email"
    EBAY = "ebay"
    FACEBOOK = "facebook"
    CRAIGSLIST = "craigslist"
    MERCARI = "mercari"
    ETSY = "etsy"
    AMAZON = "amazon"


@dataclass
class Message:
    """Unified message representation"""
    id: str
    source: MessageSource
    sender_name: str
    sender_email: str
    subject: str
    body: str
    listing_id: Optional[str]
    timestamp: datetime
    is_read: bool = False
    ai_draft_response: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['source'] = self.source.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_email(cls, email_msg: EmailMessage, listing_id: Optional[str] = None) -> 'Message':
        """Create Message from EmailMessage"""
        return cls(
            id=email_msg.id,
            source=MessageSource.EMAIL,
            sender_name=email_msg.sender_name,
            sender_email=email_msg.sender_email,
            subject=email_msg.subject,
            body=email_msg.body,
            listing_id=listing_id,
            timestamp=email_msg.timestamp,
            is_read=email_msg.is_read
        )


class MessageService:
    """
    Unified message aggregation and AI response service
    
    Fetches messages from multiple sources (eBay, Facebook, email, etc.)
    and provides AI-powered response generation.
    """
    
    def __init__(self, email_service: Optional[EmailService] = None):
        """
        Initialize message service
        
        Args:
            email_service: Optional EmailService instance
        """
        self.email_service = email_service or EmailService()
        self.request_router = RequestRouter()
        
        # In-memory storage for marketplace messages (would be database in production)
        self.marketplace_messages: Dict[MessageSource, List[Message]] = {
            source: [] for source in MessageSource
        }
    
    def get_all_messages(self, username: str) -> List[Message]:
        """
        Get all messages from all sources
        
        Args:
            username: Username to get messages for
            
        Returns:
            List of unified Message objects from all sources
        """
        messages = []
        
        # Get email messages
        email_messages = self.email_service.get_inbox(username)
        for email_msg in email_messages:
            messages.append(Message.from_email(email_msg))
        
        # Get marketplace messages
        for source_messages in self.marketplace_messages.values():
            messages.extend(source_messages)
        
        # Sort by timestamp, newest first
        return sorted(messages, key=lambda m: m.timestamp, reverse=True)
    
    def get_messages_by_source(self, username: str, source: MessageSource) -> List[Message]:
        """
        Get messages from a specific source
        
        Args:
            username: Username
            source: Message source to filter by
            
        Returns:
            List of messages from the specified source
        """
        if source == MessageSource.EMAIL:
            email_messages = self.email_service.get_inbox(username)
            return [Message.from_email(email_msg) for email_msg in email_messages]
        
        return self.marketplace_messages.get(source, [])
    
    def fetch_ebay_messages(self, username: str) -> List[Message]:
        """
        Fetch messages from eBay API
        
        Args:
            username: Username
            
        Returns:
            List of eBay messages
            
        TODO: Integrate with actual eBay API
        """
        # Placeholder for eBay API integration
        # In production, this would call eBay's Trading API GetMyMessages
        
        # Mock data for demonstration
        mock_messages = []
        
        return mock_messages
    
    def fetch_facebook_messages(self, username: str) -> List[Message]:
        """
        Fetch messages from Facebook Marketplace
        
        Args:
            username: Username
            
        Returns:
            List of Facebook messages
            
        TODO: Integrate with Facebook Graph API
        """
        # Placeholder for Facebook API integration
        # In production, this would call Facebook Graph API
        
        # Mock data for demonstration
        mock_messages = []
        
        return mock_messages
    
    def generate_ai_response(self, message: Message, listing_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate AI-powered response to a message
        
        Args:
            message: Message to respond to
            listing_context: Optional context about the listing (price, description, etc.)
            
        Returns:
            AI-generated draft response
        """
        # Prepare context
        context = listing_context or {}
        
        # Add message context
        context['message_source'] = message.source.value
        context['sender_name'] = message.sender_name
        
        # Generate response using request router
        response = self.request_router.route_request(message.body, context)
        
        # Store the AI draft on the message
        message.ai_draft_response = response
        
        return response
    
    def send_response(self, username: str, message: Message, response_text: str) -> bool:
        """
        Send a response to a message
        
        Args:
            username: Username sending the response
            message: Original message being responded to
            response_text: Response text to send
            
        Returns:
            True if sent successfully
        """
        if message.source == MessageSource.EMAIL:
            # Send via email service
            subject = f"Re: {message.subject}"
            return self.email_service.send_reply(
                username=username,
                recipient_email=message.sender_email,
                subject=subject,
                body=response_text,
                in_reply_to=message.id
            )
        
        elif message.source == MessageSource.EBAY:
            # TODO: Send via eBay API
            print(f"Sending eBay message to {message.sender_name}: {response_text}")
            return True
        
        elif message.source == MessageSource.FACEBOOK:
            # TODO: Send via Facebook API
            print(f"Sending Facebook message to {message.sender_name}: {response_text}")
            return True
        
        else:
            # Other marketplaces
            print(f"Sending {message.source.value} message to {message.sender_name}: {response_text}")
            return True
    
    def mark_as_read(self, username: str, message_id: str, source: MessageSource) -> bool:
        """
        Mark a message as read
        
        Args:
            username: Username
            message_id: Message ID
            source: Message source
            
        Returns:
            True if marked, False if not found
        """
        if source == MessageSource.EMAIL:
            return self.email_service.mark_as_read(username, message_id)
        
        # For marketplace messages
        if source in self.marketplace_messages:
            for message in self.marketplace_messages[source]:
                if message.id == message_id:
                    message.is_read = True
                    return True
        
        return False
    
    def get_unread_count(self, username: str) -> int:
        """
        Get total unread message count across all sources
        
        Args:
            username: Username
            
        Returns:
            Total unread count
        """
        count = 0
        
        # Email unread count
        count += self.email_service.get_unread_count(username)
        
        # Marketplace unread counts
        for source_messages in self.marketplace_messages.values():
            count += sum(1 for msg in source_messages if not msg.is_read)
        
        return count
    
    def add_marketplace_message(self, source: MessageSource, sender_name: str,
                               sender_email: str, subject: str, body: str,
                               listing_id: Optional[str] = None) -> Message:
        """
        Add a message from a marketplace (for testing/demo purposes)
        
        Args:
            source: Message source
            sender_name: Sender's name
            sender_email: Sender's email/ID
            subject: Message subject
            body: Message body
            listing_id: Optional listing ID
            
        Returns:
            Created Message object
        """
        message = Message(
            id=str(uuid.uuid4()),
            source=source,
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            body=body,
            listing_id=listing_id,
            timestamp=datetime.now(),
            is_read=False
        )
        
        if source not in self.marketplace_messages:
            self.marketplace_messages[source] = []
        
        self.marketplace_messages[source].append(message)
        
        return message


# Example usage
if __name__ == "__main__":
    # Initialize services
    email_service = EmailService()
    message_service = MessageService(email_service)
    
    # Create user alias
    username = "john_doe"
    email_service.create_alias(username)
    
    # Simulate incoming messages from different sources
    print("Simulating incoming messages...")
    
    # Email message
    email_service.receive_email(
        username=username,
        sender_name="Jane Buyer",
        sender_email="jane@example.com",
        subject="Is this still available?",
        body="Hi! I'm interested in the vintage lamp. Is it still available?"
    )
    
    # eBay message
    message_service.add_marketplace_message(
        source=MessageSource.EBAY,
        sender_name="Bob Smith",
        sender_email="bob_smith_ebay",
        subject="Question about item",
        body="What's the lowest you'll go on this?",
        listing_id="ebay_12345"
    )
    
    # Facebook message
    message_service.add_marketplace_message(
        source=MessageSource.FACEBOOK,
        sender_name="Alice Johnson",
        sender_email="alice_fb",
        subject="Shipping question",
        body="Can you ship to New York?",
        listing_id="fb_67890"
    )
    print()
    
    # Get all messages
    print("All messages:")
    all_messages = message_service.get_all_messages(username)
    for msg in all_messages:
        print(f"[{msg.source.value}] {msg.sender_name}: {msg.subject}")
    print()
    
    # Generate AI responses
    print("Generating AI responses...")
    for msg in all_messages:
        response = message_service.generate_ai_response(msg, {"price": 100.00})
        print(f"\nMessage: {msg.body}")
        print(f"AI Response: {response}")
    print()
    
    # Check unread count
    unread = message_service.get_unread_count(username)
    print(f"Total unread messages: {unread}")
