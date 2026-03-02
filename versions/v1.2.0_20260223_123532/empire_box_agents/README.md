# Empire Box Agents

A comprehensive safeguards and emergency stop system for autonomous agents.

## What Can You Do?

Empire Box Agents provides essential safety mechanisms for autonomous agent systems:

- ✅ **Emergency Stop**: Manual and automatic shutdown capabilities
- ✅ **Rate Limiting**: Control action frequency to prevent abuse
- ✅ **Budget Management**: Limit total actions to control costs
- ✅ **Action Whitelisting**: Restrict operations to approved actions only
- ✅ **State Preservation**: Save agent state during shutdowns
- ✅ **Admin Alerting**: Notify administrators of critical events
- ✅ **Thread Safety**: Secure concurrent operation handling

## Quick Start

```python
from emergency_stop import EmergencyStop
from safeguards import AgentSafeguards

# Create safeguards
safeguards = AgentSafeguards(
    rate_limit=10,  # 10 actions per minute
    budget=100,     # 100 total actions
    action_whitelist=["read", "write", "analyze"]
)

# Create emergency stop
emergency = EmergencyStop()

# Execute actions safely
try:
    safeguards.can_execute_action("read")
    # Perform the action
except Exception as e:
    emergency.manual_trigger()
```

## Files

- **`emergency_stop.py`**: Emergency stop protocol implementation
- **`safeguards.py`**: Rate limiting, budgets, and action whitelisting
- **`integration_guide.py`**: Complete integration example and demonstration
- **`CAPABILITIES.md`**: Comprehensive capabilities documentation

## Features in Detail

### Emergency Stop System

Provides immediate shutdown capabilities with state preservation:

```python
emergency = EmergencyStop()

# Manual trigger
emergency.manual_trigger()

# Automatic trigger based on conditions
emergency.auto_trigger()
```

**Capabilities:**
- Manual emergency shutdown
- Automatic failure detection
- State saving before shutdown
- Administrator alerting
- Status tracking

### Safeguards System

Controls agent behavior with multiple protection layers:

```python
safeguards = AgentSafeguards(
    rate_limit=5,   # Max actions per minute
    budget=50,      # Total action budget
    action_whitelist=["action1", "action2"]
)

# Check before executing action
safeguards.can_execute_action("action1")
```

**Capabilities:**
- Rate limiting (actions per minute)
- Budget tracking and enforcement
- Action whitelisting
- Thread-safe operations
- Budget refill support
- Emergency budget zeroing

## Integration Example

See `integration_guide.py` for a complete example of combining both systems:

```bash
python integration_guide.py
```

This demonstrates:
- Creating a protected agent
- Executing actions with safeguards
- Handling rate limits and budgets
- Triggering emergency stops
- Logging and monitoring

## Testing

Run the test suite:

```bash
python test_emergency_stop.py
python test_safeguards.py
```

## Use Cases

### Development
- Test agent behaviors safely
- Experiment with different configurations
- Debug agent operations

### Production
- Prevent runaway agents
- Control operational costs
- Ensure compliance with action policies
- Emergency intervention capabilities

### High-Security
- Strict action controls
- Minimal attack surface
- Comprehensive audit trails
- Immediate shutdown on anomalies

## Documentation

- **Quick Reference**: This README
- **Detailed Capabilities**: See `CAPABILITIES.md`
- **Integration Guide**: See `integration_guide.py`
- **Code Examples**: See `__main__` sections in source files

## Safety Best Practices

1. **Set conservative limits** initially
2. **Monitor agent behavior** regularly
3. **Test emergency stops** before deployment
4. **Keep action whitelists minimal**
5. **Review logs frequently**
6. **Have manual intervention procedures**

## Advanced Usage

### Custom Failure Detection

```python
class CustomEmergencyStop(EmergencyStop):
    def detect_failure_conditions(self):
        # Custom logic here
        if some_critical_condition():
            return True
        return False
```

### Dynamic Rate Limits

```python
# Adjust rate limits at runtime
safeguards.rate_limit = 20  # Increase during off-peak
```

### Integration with Monitoring

```python
def monitor_agent():
    safeguards.monitor()
    if safeguards.current_balance < 10:
        send_alert("Budget running low")
```

## Support

For detailed documentation on all capabilities, see `CAPABILITIES.md`.

## License

See LICENSE file in the repository root.
