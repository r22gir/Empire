"""
Integration Guide: How to Use Empire Box Agents

This module demonstrates how to integrate and use the emergency stop
and safeguards systems together in a real-world application.
"""

from emergency_stop import EmergencyStop
from safeguards import AgentSafeguards
import time


class EnhancedAgent:
    """
    An enhanced agent that combines emergency stop and safeguard features.
    
    This demonstrates what you can do with the Empire Box Agents system.
    """
    
    def __init__(self, rate_limit=10, budget=100, allowed_actions=None):
        """
        Initialize the enhanced agent with protective measures.
        
        Args:
            rate_limit: Maximum actions per minute
            budget: Total action budget
            allowed_actions: List of permitted action types
        """
        if allowed_actions is None:
            allowed_actions = ["read", "write", "compute", "network"]
        
        self.emergency_stop = EmergencyStop()
        self.safeguards = AgentSafeguards(
            rate_limit=rate_limit,
            budget=budget,
            action_whitelist=allowed_actions
        )
        self.action_count = 0
        self.error_count = 0
        self.action_log = []
    
    def execute(self, action, data=None):
        """
        Execute an action with full protection.
        
        Args:
            action: The action type to execute
            data: Optional data for the action
            
        Returns:
            Result of the action or error message
        """
        # Check if emergency stop is active
        if not self.emergency_stop.is_running:
            return {
                "success": False,
                "error": "Agent is in emergency stop mode"
            }
        
        try:
            # Check safeguards
            self.safeguards.can_execute_action(action)
            
            # Execute the action
            result = self._perform_action(action, data)
            
            # Log success
            self.action_count += 1
            self._log_action(action, "success", result)
            
            return {
                "success": True,
                "action": action,
                "result": result,
                "action_count": self.action_count
            }
            
        except Exception as e:
            # Log error
            self.error_count += 1
            self._log_action(action, "error", str(e))
            
            # Check if we should trigger emergency stop
            if self._should_emergency_stop(str(e)):
                self.emergency_stop.auto_trigger()
            
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "error_count": self.error_count
            }
    
    def _perform_action(self, action, data):
        """
        Simulate action execution.
        
        In a real implementation, this would perform actual work.
        """
        if action == "read":
            return f"Read data: {data}"
        elif action == "write":
            return f"Wrote data: {data}"
        elif action == "compute":
            return f"Computed: {data}"
        elif action == "network":
            return f"Network call with: {data}"
        else:
            return f"Unknown action: {action}"
    
    def _log_action(self, action, status, details):
        """Log action for audit trail."""
        self.action_log.append({
            "timestamp": time.time(),
            "action": action,
            "status": status,
            "details": details
        })
    
    def _should_emergency_stop(self, error_msg):
        """
        Determine if an error should trigger emergency stop.
        
        Args:
            error_msg: The error message
            
        Returns:
            True if emergency stop should be triggered
        """
        critical_keywords = [
            "budget exhausted",
            "critical failure",
            "security breach",
            "unauthorized"
        ]
        
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in critical_keywords)
    
    def get_status(self):
        """
        Get current agent status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "running": self.emergency_stop.is_running,
            "actions_executed": self.action_count,
            "errors": self.error_count,
            "budget_remaining": self.safeguards.current_balance,
            "manual_stop_triggered": self.emergency_stop.manual_triggered,
            "state_saved": self.emergency_stop.state_saved
        }
    
    def refill_budget(self, amount):
        """Refill the action budget."""
        self.safeguards.refill_budget(amount)
        print(f"Budget refilled by {amount}")
    
    def manual_stop(self):
        """Manually trigger emergency stop."""
        self.emergency_stop.manual_trigger()
        print("Manual emergency stop activated")
    
    def get_action_log(self, limit=10):
        """
        Get recent action log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of recent log entries
        """
        return self.action_log[-limit:]


def demonstrate_capabilities():
    """
    Demonstrate what you can do with Empire Box Agents.
    """
    print("=" * 60)
    print("Empire Box Agents - Capability Demonstration")
    print("=" * 60)
    print()
    
    # Create an agent with constraints
    print("1. Creating agent with safeguards...")
    agent = EnhancedAgent(
        rate_limit=60,  # 60 actions per minute = 1 per second
        budget=10,
        allowed_actions=["read", "write", "compute"]
    )
    print(f"   Status: {agent.get_status()}")
    print()
    
    # Execute some actions
    print("2. Executing allowed actions...")
    for i in range(3):
        result = agent.execute("read", f"data_{i}")
        print(f"   Action {i+1}: {result}")
        time.sleep(1.1)  # Respect rate limit (1 per second)
    print()
    
    # Try an unauthorized action
    print("3. Attempting unauthorized action...")
    result = agent.execute("delete", "important_data")
    print(f"   Result: {result}")
    print()
    
    # Refill budget
    print("4. Refilling budget...")
    agent.refill_budget(5)
    print(f"   Status: {agent.get_status()}")
    print()
    
    # Execute more actions
    print("5. Executing more actions...")
    for i in range(2):
        result = agent.execute("write", f"output_{i}")
        print(f"   Action {i+1}: {result}")
        time.sleep(1.1)  # Respect rate limit
    print()
    
    # Show action log
    print("6. Recent action log:")
    for entry in agent.get_action_log(5):
        print(f"   {entry}")
    print()
    
    # Trigger manual stop
    print("7. Triggering manual emergency stop...")
    agent.manual_stop()
    print(f"   Status: {agent.get_status()}")
    print()
    
    # Try to execute after stop
    print("8. Attempting action after emergency stop...")
    result = agent.execute("read", "data")
    print(f"   Result: {result}")
    print()
    
    print("=" * 60)
    print("Demonstration Complete!")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_capabilities()
