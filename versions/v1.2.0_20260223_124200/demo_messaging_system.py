"""
Visual Mock Data Generator for Testing
Demonstrates the messaging system with realistic sample data
"""

from empire_box_agents.email_service import EmailService
from empire_box_agents.message_service import MessageService, MessageSource
from datetime import datetime, timedelta


def create_demo_data():
    """Create demonstration data for the messaging system"""
    
    # Initialize services
    email_service = EmailService()
    message_service = MessageService(email_service)
    
    # Create user
    username = "demo_seller"
    email_service.create_alias(username)
    
    print("=" * 80)
    print("MARKETFORGE UNIFIED MESSAGING SYSTEM - DEMO")
    print("=" * 80)
    print()
    
    # Create sample messages from different sources
    now = datetime.now()
    
    # Email messages
    email_service.receive_email(
        username=username,
        sender_name="Sarah Johnson",
        sender_email="sarah.j@gmail.com",
        subject="Question about vintage camera",
        body="Hi! I'm interested in the vintage Nikon camera you have listed. Is it still available? Also, does it come with the original case?"
    )
    
    email_service.receive_email(
        username=username,
        sender_name="Michael Chen",
        sender_email="m.chen@outlook.com",
        subject="Shipping to Canada",
        body="Hello, I'd like to purchase the leather jacket. Do you ship to Toronto, Canada?"
    )
    
    # eBay messages
    message_service.add_marketplace_message(
        source=MessageSource.EBAY,
        sender_name="TechCollector99",
        sender_email="techcollector99_ebay",
        subject="Best offer for vintage watch",
        body="What's the lowest you'll go on the vintage Omega watch? I'm a serious buyer.",
        listing_id="ebay_456789"
    )
    
    message_service.add_marketplace_message(
        source=MessageSource.EBAY,
        sender_name="RetroGamer2000",
        sender_email="retrogamer_ebay",
        subject="Question about Nintendo Game Boy",
        body="Does the Game Boy still work? Are there any dead pixels on the screen?",
        listing_id="ebay_123456"
    )
    
    # Facebook Marketplace messages
    message_service.add_marketplace_message(
        source=MessageSource.FACEBOOK,
        sender_name="Emily Rodriguez",
        sender_email="emily_fb_12345",
        subject="Interested in dining table",
        body="Is this still available? Can I come see it today?",
        listing_id="fb_789012"
    )
    
    message_service.add_marketplace_message(
        source=MessageSource.FACEBOOK,
        sender_name="David Park",
        sender_email="david_fb_67890",
        subject="Pickup time for bicycle",
        body="I'd like to buy the bicycle. What time can I pick it up tomorrow?",
        listing_id="fb_345678"
    )
    
    # Craigslist messages
    message_service.add_marketplace_message(
        source=MessageSource.CRAIGSLIST,
        sender_name="Anonymous User",
        sender_email="reply-54321@craigslist.org",
        subject="Re: Furniture for sale",
        body="Hi, is the couch pet-free and smoke-free? Would you take $150 for it?",
        listing_id="cl_901234"
    )
    
    # Display all messages
    print(f"\n📧 Email Address: {username}@marketforge.app")
    print()
    
    messages = message_service.get_all_messages(username)
    total_unread = message_service.get_unread_count(username)
    
    print(f"📬 INBOX ({len(messages)} messages, {total_unread} unread)")
    print("-" * 80)
    print()
    
    for i, msg in enumerate(messages, 1):
        # Source icon
        source_icons = {
            MessageSource.EMAIL: "📧",
            MessageSource.EBAY: "🛍️",
            MessageSource.FACEBOOK: "📘",
            MessageSource.CRAIGSLIST: "📋",
            MessageSource.MERCARI: "🏪",
            MessageSource.ETSY: "🎨",
            MessageSource.AMAZON: "📦",
        }
        icon = source_icons.get(msg.source, "💬")
        
        # Read status
        status = "🔵" if not msg.is_read else "  "
        
        print(f"{status} {icon} [{msg.source.value.upper()}] {msg.sender_name}")
        print(f"   Subject: {msg.subject}")
        print(f"   Message: {msg.body[:70]}{'...' if len(msg.body) > 70 else ''}")
        
        # Generate and display AI response
        context = {"price": 150.00} if "lowest" in msg.body.lower() else {}
        ai_response = message_service.generate_ai_response(msg, context)
        
        print(f"   ✨ AI Draft: {ai_response[:60]}{'...' if len(ai_response) > 60 else ''}")
        print()
    
    print("-" * 80)
    print()
    
    # Show filtering by source
    print("📊 MESSAGES BY SOURCE:")
    print("-" * 80)
    
    sources = [
        MessageSource.EMAIL,
        MessageSource.EBAY,
        MessageSource.FACEBOOK,
        MessageSource.CRAIGSLIST
    ]
    
    for source in sources:
        source_messages = message_service.get_messages_by_source(username, source)
        if source_messages:
            icon = source_icons.get(source, "💬")
            print(f"{icon} {source.value.upper()}: {len(source_messages)} messages")
    
    print()
    print("=" * 80)
    print()
    
    # Demonstrate sending a reply
    print("📤 SENDING REPLY EXAMPLE:")
    print("-" * 80)
    first_message = messages[0]
    print(f"To: {first_message.sender_name} ({first_message.sender_email})")
    print(f"Re: {first_message.subject}")
    print()
    print(f"Reply: {first_message.ai_draft_response}")
    print()
    
    success = message_service.send_response(
        username=username,
        message=first_message,
        response_text=first_message.ai_draft_response or "Thank you for your interest!"
    )
    
    if success:
        print("✅ Reply sent successfully!")
    else:
        print("❌ Failed to send reply")
    
    print()
    print("=" * 80)
    print()
    
    return message_service


if __name__ == "__main__":
    create_demo_data()
