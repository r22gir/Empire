# MarketForge Unified Messaging System - Features & Usage

## Features Overview

### 🎯 Core Features

#### 1. Unified Inbox
- **All Messages in One Place**: View messages from eBay, Facebook Marketplace, Craigslist, Email, and more in a single unified inbox
- **Source Filtering**: Filter messages by source (All, eBay, Facebook, Email, etc.)
- **Real-time Updates**: Pull-to-refresh to get latest messages
- **Unread Tracking**: Badge on Messages tab shows total unread count across all sources

#### 2. Email Alias System
- **Dedicated Email Address**: Each user gets `username@marketforge.app` 
- **Copy to Clipboard**: Easy one-tap copy of your email address
- **Email Forwarding**: Forward from personal email to MarketForge inbox
- **Custom Domain** (Pro): Use your own domain (e.g., `username@yourdomain.com`)

#### 3. AI-Powered Responses
- **Automatic Draft Generation**: AI analyzes buyer messages and generates contextual responses
- **Smart Routing**: Simple queries handled locally for speed, complex queries use cloud AI
- **Context-Aware**: AI considers listing details, pricing, and conversation context
- **Three Actions**:
  - **Send**: Send AI draft as-is
  - **Edit**: Modify the draft before sending
  - **Regenerate**: Generate a new response

#### 4. Multi-Source Support
Supported marketplace sources:
- 📧 **Email** - Direct email messages
- 🛍️ **eBay** - eBay messages (API integration ready)
- 📘 **Facebook** - Facebook Marketplace messages (API integration ready)
- 📋 **Craigslist** - Craigslist replies
- 🏪 **Mercari** - Mercari messages
- 🎨 **Etsy** - Etsy conversations
- 📦 **Amazon** - Amazon messages

## UI Components

### Messages Screen
```
┌─────────────────────────────────────┐
│  Messages            🔍 [Filter] ⚙️  │
├─────────────────────────────────────┤
│                                     │
│  🔵 📧 Jane Buyer                   │
│     Is this still available?        │
│     Hi! I'm interested in...        │
│     2h ago                          │
│     ✨ AI: Yes! It's still avai...  │
│                                     │
│  🔵 🛍️ Bob Smith - eBay             │
│     Question about item             │
│     What's the lowest you'll...     │
│     5h ago                          │
│     ✨ AI: I can do $90.00...       │
│                                     │
│     📘 Alice Johnson - Facebook     │
│     Shipping question               │
│     Can you ship to New York?       │
│     1d ago                          │
│                                     │
└─────────────────────────────────────┘
```

### Message Detail Screen
```
┌─────────────────────────────────────┐
│  ← Jane Buyer                       │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐   │
│  │ 👤 Jane Buyer               │   │
│  │    jane@example.com         │   │
│  │    📧 Email                 │   │
│  │                             │   │
│  │ Is this still available?    │   │
│  │ 2 hours ago                 │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Hi! I'm interested in the   │   │
│  │ vintage lamp. Is it still   │   │
│  │ available?                   │   │
│  └─────────────────────────────┘   │
│                                     │
│  🔗 Related Listing: lamp_12345     │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ ✨ AI Draft Response        │   │
│  │                             │   │
│  │ Yes! It's still available.  │   │
│  │ Ready to ship today!        │   │
│  │                             │   │
│  │ [Edit] [Regenerate] [Send]  │   │
│  └─────────────────────────────┘   │
│                                     │
├─────────────────────────────────────┤
│  Type your reply...           [📤] │
└─────────────────────────────────────┘
```

### Email Settings Screen
```
┌─────────────────────────────────────┐
│  ← Email Settings                   │
├─────────────────────────────────────┤
│  Your MarketForge Email             │
│  ┌─────────────────────────────┐   │
│  │ demo_user@marketforge.app   │📋 │
│  └─────────────────────────────┘   │
│                                     │
│  Email Forwarding                   │
│  ⚫ Enable Forwarding               │
│                                     │
│  Custom Domain              [PRO]   │
│  ┌─────────────────────────────┐   │
│  │ yourdomain.com (disabled)   │   │
│  └─────────────────────────────┘   │
│  [Upgrade to Pro]                   │
│                                     │
│  Test Your Email                    │
│  [Send Test Email]                  │
└─────────────────────────────────────┘
```

## AI Response Examples

### Availability Queries
**Buyer**: "Is this still available?"  
**AI Response**: "Yes! It's still available. Ready to ship today!"

**Buyer**: "Do you still have this?"  
**AI Response**: "Yes! It's still available. Ready to ship today!"

### Shipping Queries
**Buyer**: "Can you ship to California?"  
**AI Response**: "Yes! I can ship to California. Shipping cost will be calculated based on the item's weight and dimensions."

**Buyer**: "Do you ship to New York?"  
**AI Response**: "Yes! I can ship to New York. Shipping cost will be calculated based on the item's weight and dimensions."

### Price Negotiation
**Buyer**: "What's the lowest you'll go?"  
**AI Response** (with $100 listing): "I can do $90.00, that's my best price for this quality item."

**Buyer**: "Will you take $50?"  
**AI Response**: "I have some flexibility on the price. What did you have in mind?"

**Buyer**: "Are you firm on the price?"  
**AI Response** (with context): "I can do $90.00, that's my best price for this quality item."

### Generic Queries
**Buyer**: "I have several questions about the condition, history, and whether you have any similar items."  
**AI Response**: "Thanks for your message! Let me provide you with detailed information. Feel free to ask any follow-up questions you might have."

## Usage Workflow

### For Sellers

#### Daily Message Management
1. Open MarketForge app
2. Check Messages tab (unread count visible on badge)
3. View unified inbox with all messages
4. Tap any message to view details

#### Responding to Buyers
1. Open message detail
2. Tap "Generate" to create AI draft response
3. Choose action:
   - **Send**: Send AI response immediately
   - **Edit**: Modify response before sending
   - **Regenerate**: Create a new AI draft
4. Or type custom reply in text field
5. Tap send button

#### Managing Multiple Sources
1. Use filter dropdown in Messages screen
2. Select specific source (eBay, Facebook, etc.)
3. View only messages from that source
4. Clear filter to see all messages again

#### Email Setup
1. Go to Settings → Email Settings
2. View your @marketforge.app address
3. Copy to clipboard to use in listings
4. (Optional) Set up forwarding from personal email
5. (Pro users) Configure custom domain

## Technical Architecture

### Backend (Python)
```
empire_box_agents/
├── request_router.py      # AI routing logic
├── email_service.py       # Email alias management
└── message_service.py     # Unified message aggregation
```

### Frontend (Flutter)
```
market_forge_app/lib/
├── main.dart                    # App entry & navigation
├── models/
│   └── message.dart             # Data models
├── services/
│   └── message_service.dart     # API client
├── providers/
│   └── message_provider.dart    # State management
├── screens/
│   ├── messages_screen.dart     # Inbox view
│   ├── message_detail_screen.dart  # Detail view
│   └── email_settings_screen.dart  # Settings
└── widgets/
    └── message_tile.dart        # Message list item
```

## API Integration Points

### Current Status
- ✅ Backend services functional
- ✅ Flutter UI complete
- ⏳ REST API wrapper needed
- ⏳ Email webhook integration
- ⏳ Marketplace API connections

### Future Integrations
1. **eBay Trading API**: GetMyMessages endpoint
2. **Facebook Graph API**: Conversations endpoint
3. **Cloudflare Email Routing**: Email forwarding webhook
4. **Cloud AI**: OpenAI/Anthropic integration for complex queries

## Testing

### Run Backend Demo
```bash
cd /home/runner/work/Empire/Empire
python demo_messaging_system.py
```

This demonstrates:
- Creating messages from multiple sources
- AI response generation
- Unified inbox aggregation
- Filtering by source
- Sending replies

### Run Flutter App
```bash
cd market_forge_app
flutter pub get
flutter run
```

The app will display mock data until backend API is connected.

## Benefits for Resellers

### Time Savings
- **No Platform Switching**: Check all messages in one app
- **AI Drafts**: Respond 10x faster with AI assistance
- **Quick Replies**: Common questions answered instantly

### Organization
- **Unified Inbox**: All communications in one place
- **Source Filtering**: Easily separate eBay, Facebook, email
- **Unread Tracking**: Never miss an important message

### Professionalism
- **Dedicated Email**: Professional @marketforge.app address
- **Consistent Responses**: AI ensures quality replies
- **Faster Response Time**: Reply within minutes, not hours

### Privacy
- **Separate Email**: Keep sales communication away from personal email
- **No Platform Dependency**: Own your customer relationships
- **Data Control**: All messages stored in your account

## Future Enhancements

### Short Term
- Message templates
- Bulk actions (archive, delete)
- Search functionality
- Push notifications

### Medium Term
- Conversation threading
- Attachment support
- Scheduled messages
- Auto-responder for common questions

### Long Term
- Analytics dashboard (response time, conversion rate)
- Multi-language support
- CRM integration
- Custom AI training on your responses

## Support

For questions or issues:
- Check documentation in `MESSAGING_SYSTEM_README.md`
- Review demo script: `demo_messaging_system.py`
- Test backend: `python empire_box_agents/message_service.py`

---

**MarketForge** - Simplifying reselling, one message at a time.
