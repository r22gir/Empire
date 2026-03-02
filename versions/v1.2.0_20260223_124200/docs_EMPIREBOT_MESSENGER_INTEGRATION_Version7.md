# EmpireBot - Messenger Integration for EmpireBox

## Overview
EmpireBot allows users to manage their entire EmpireBox business via Telegram, WhatsApp, or SMS. 
Powered by OpenClaw AI for natural language understanding.

## Supported Channels
- **Telegram** (Phase 1) - Free, easy API, recommended
- **WhatsApp Business** (Phase 2) - Via Twilio or Meta API
- **SMS** (Phase 2) - Via Twilio
- **Slack/Discord** (Phase 3) - Team collaboration

## Core Features
- Check orders, inventory, revenue
- Create listings via photo + text
- Generate shipping labels
- Manage calendar and tasks
- Handle support tickets
- Get proactive notifications

## Technical Stack
- Python/Node.js backend
- Redis for message queuing
- PostgreSQL for conversation history
- OpenClaw AI for intent parsing
- REST APIs to all EmpireBox sub-products

## Commands (Telegram MVP)
- `/start` - Link account
- `/orders` - Today's orders
- `/ship <id>` - Create label
- `/balance` - Stripe balance
- `/tasks` - Pending tasks
- `/help` - All commands

## Pricing
- Basic: Included with EmpireBox (100 msg/month)
- Pro: $19/month (unlimited)
- Business: $49/month (+ SMS, voice, team)

## Inspiration
Based on AI automation business models (ref: Alex Finn YouTube)