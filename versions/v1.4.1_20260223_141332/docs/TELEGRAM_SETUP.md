# Telegram Bot Setup Guide

Control and monitor your EmpireBox remotely via Telegram.

## Prerequisites

- EmpireBox installed and running
- A Telegram account

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** you receive (looks like `123456:ABC-...`)

---

## Step 2 — Get Your Telegram User ID

1. Open Telegram and search for **@userinfobot**
2. Send `/start` — it will reply with your numeric user ID (e.g. `123456789`)

---

## Step 3 — Configure the Bot

Edit `/opt/empirebox/telegram/config.yaml`:

```yaml
telegram:
  bot_token: "123456:ABC-your-actual-token"

  allowed_users:
    - 123456789   # Replace with your Telegram user ID

  pin_enabled: false   # Set to true to require a PIN for destructive commands
  pin_code: "1234"

  pin_required_commands:
    - stop_product
    - stop_all
    - restart

  rate_limit:
    max_commands_per_minute: 30

  notifications:
    enabled: true
    system_alerts: true
    product_crashes: true
    daily_summary: false
    daily_summary_time: "09:00"

openclaw:
  host: "http://openclaw:7878"
  timeout: 30
```

---

## Step 4 — Add Bot Token to the Environment

Edit `/opt/empirebox/.env` and set:

```
TELEGRAM_BOT_TOKEN=123456:ABC-your-actual-token
```

---

## Step 5 — Start the Bot

```bash
ebox telegram start
```

Check status:

```bash
ebox telegram status
```

View logs:

```bash
ebox telegram logs
```

Stop the bot:

```bash
ebox telegram stop
```

---

## Step 6 — Test the Bot

Open Telegram, find your bot by the username you gave it in Step 1, and send:

```
/start
```

You should receive a welcome message.

---

## Available Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and setup info |
| `/status` | Show running products |
| `/list` | List all products with status |
| `/start_product <name>` | Start a product (e.g. `/start_product marketforge`) |
| `/stop_product <name>` | Stop a product |
| `/bundle <name>` | Start a bundle (`reseller`, `contractor`, `support`, `full`) |
| `/logs <product>` | Get recent logs for a product |
| `/health` | Full system health check |
| `/backup` | Trigger database backup |
| `/help` | Show all commands |

You can also send **natural language** messages:

- "What's running right now?"
- "Start MarketForge"
- "How much disk space is left?"
- "Show me the last errors"

The bot forwards these to the OpenClaw AI agent and returns the response.

---

## Security

### Whitelist

Only users listed in `allowed_users` can interact with the bot. All other messages are silently rejected.

### PIN Protection

If `pin_enabled: true`, commands in `pin_required_commands` will ask for the PIN before executing. Once verified, the PIN is cached for the session.

### Rate Limiting

Each user is limited to `max_commands_per_minute` commands (default: 30). Exceeding the limit returns an error message.

### Audit Log

All commands are logged by the bot container. View them with:

```bash
ebox telegram logs
```

---

## Notifications

The bot automatically sends alerts to all `allowed_users` when:

- **CPU / Memory / Disk** exceeds 90% (with a 5-minute cooldown between repeated alerts)
- A **product container crashes** (sent by OpenClaw or the bot)
- A **backup completes** (success or failure)

Configure under `notifications:` in `config.yaml`.

---

## Troubleshooting

**Bot does not respond**
- Check the token in `config.yaml` and `.env` match the one from @BotFather
- Run `ebox telegram logs` for error messages
- Make sure the openclaw service is running: `docker ps | grep openclaw`

**"Access denied" message**
- Add your Telegram user ID to `allowed_users` in `config.yaml`, then restart:
  `ebox telegram stop && ebox telegram start`

**OpenClaw not reachable**
- Verify `ebox status` shows openclaw is running
- Check the `openclaw.host` value in `config.yaml`
