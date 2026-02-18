# Empire

A comprehensive system combining agent safeguards, emergency stop protocols, and mobile marketplace functionality.

## What Can You Do?

Empire provides multiple powerful capabilities across different domains:

### 🛡️ Empire Box Agents - Agent Safety System

A production-ready safeguards and emergency stop system for autonomous agents.

**Key Capabilities:**
- ✅ Emergency stop (manual and automatic)
- ✅ Rate limiting (actions per minute)
- ✅ Budget management (total action limits)
- ✅ Action whitelisting (approved operations only)
- ✅ State preservation during shutdown
- ✅ Administrator alerting
- ✅ Thread-safe operations

**Quick Example:**
```python
from empire_box_agents.emergency_stop import EmergencyStop
from empire_box_agents.safeguards import AgentSafeguards

# Create safeguards
safeguards = AgentSafeguards(
    rate_limit=60,     # 60 actions per minute
    budget=100,        # 100 total actions
    action_whitelist=["read", "write", "analyze"]
)

# Execute actions safely
try:
    safeguards.can_execute_action("read")
    # Perform your action here
except Exception as e:
    print(f"Action blocked: {e}")
```

**Documentation:** See [empire_box_agents/README.md](empire_box_agents/README.md) for complete documentation.

**Try it out:**
```bash
# Run the integration demo
python empire_box_agents/integration_guide.py

# Run tests
python empire_box_agents/test_emergency_stop.py
python empire_box_agents/test_safeguards.py
```

### 📱 Market Forge - Mobile Marketplace App

A Flutter-based mobile application for marketplace functionality.

**Features:**
- User Authentication (login and registration)
- Dashboard with user insights
- Marketplace for browsing and purchasing
- Real-time notifications and alerts

**Setup:**
```bash
cd market_forge_app
flutter pub get
flutter run
```

**Documentation:** See [market_forge_README.md](market_forge_README.md) for details.

## Repository Structure

```
Empire/
├── empire_box_agents/          # Agent safeguards system (Python)
│   ├── emergency_stop.py       # Emergency stop protocol
│   ├── safeguards.py          # Rate limiting and budget management
│   ├── integration_guide.py   # Complete usage example
│   ├── test_emergency_stop.py # Unit tests
│   ├── test_safeguards.py     # Unit tests
│   ├── README.md              # Agent system documentation
│   └── CAPABILITIES.md        # Detailed capabilities guide
├── market_forge_app/          # Flutter mobile app
│   └── pubspec.yaml          # Flutter dependencies
├── market_forge_README.md    # Mobile app documentation
├── LICENSE                   # Proprietary license
└── README.md                # This file
```

## Getting Started

### Empire Box Agents (Python)

**Requirements:**
- Python 3.6+
- No external dependencies (uses only standard library)

**Usage:**
```python
from empire_box_agents.integration_guide import EnhancedAgent

# Create a protected agent
agent = EnhancedAgent(
    rate_limit=10,
    budget=100,
    allowed_actions=["read", "write"]
)

# Execute actions
result = agent.execute("read", "data")
print(result)

# Check status
status = agent.get_status()
print(status)
```

### Market Forge App (Flutter)

**Requirements:**
- Flutter SDK 2.12.0+
- Dart

**Installation:**
```bash
git clone https://github.com/r22gir/Empire.git
cd Empire/market_forge_app
flutter pub get
flutter run
```

## Features in Detail

### Agent Safeguards System

**What can you do with it?**

1. **Prevent Runaway Agents**
   - Set rate limits to prevent excessive API calls
   - Define budgets to control total operations
   - Emergency stop when things go wrong

2. **Control Agent Behavior**
   - Whitelist only approved actions
   - Track all agent operations
   - Monitor performance in real-time

3. **Ensure Safety**
   - Automatic failure detection
   - State preservation before shutdown
   - Administrator alerts for issues

4. **Production Ready**
   - Thread-safe operations
   - Comprehensive test coverage
   - Well-documented API

**Use Cases:**
- AI agent safety systems
- Automated trading bots with risk controls
- Robotic process automation (RPA) safeguards
- API rate limiting and cost control
- Development and testing environments

### Market Forge App

**What can you do with it?**

1. **User Management**
   - Secure authentication
   - User profiles and preferences

2. **Marketplace**
   - Browse products
   - Purchase items
   - Track orders

3. **Engagement**
   - Real-time notifications
   - User feedback mechanisms

## Development Roadmap

### Q1 2026
- ✅ Agent safeguards system implementation
- ✅ Emergency stop protocols
- ✅ Comprehensive documentation and tests
- ⏳ User feedback mechanism for Market Forge

### Q2 2026
- 🔮 Expand marketplace features
- 🔮 Advanced agent monitoring dashboard
- 🔮 Machine learning-based failure prediction

### Q3 2026
- 🔮 Improve performance and scalability
- 🔮 Multi-tier budget systems
- 🔮 Distributed safeguard coordination

## Testing

### Agent System Tests

```bash
# Run all tests
cd empire_box_agents
python test_emergency_stop.py  # 10/10 tests pass
python test_safeguards.py      # 15/15 tests pass

# Run integration demo
python integration_guide.py
```

**Test Coverage:**
- Emergency stop functionality (manual and automatic)
- Rate limiting enforcement
- Budget management
- Action whitelisting
- Thread safety
- Edge cases and error conditions

## Contributing

This is a proprietary repository. Please see the [LICENSE](LICENSE) file for usage restrictions.

## Documentation

- **Agent System Overview**: [empire_box_agents/README.md](empire_box_agents/README.md)
- **Detailed Capabilities**: [empire_box_agents/CAPABILITIES.md](empire_box_agents/CAPABILITIES.md)
- **Integration Guide**: [empire_box_agents/integration_guide.py](empire_box_agents/integration_guide.py)
- **Mobile App**: [market_forge_README.md](market_forge_README.md)

## Support

For questions or issues, please refer to the documentation files or contact the repository owner.

## License

This project is proprietary. See [LICENSE](LICENSE) for full details.

---

**Empire** - Building safe, controlled systems for autonomous agents and marketplace applications.
