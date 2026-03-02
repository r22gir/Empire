"""
Unit tests for the AgentSafeguards system.

Run with: python test_safeguards.py
"""

import unittest
import time
import threading
from safeguards import AgentSafeguards


class TestAgentSafeguards(unittest.TestCase):
    """Test cases for AgentSafeguards functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.safeguards = AgentSafeguards(
            rate_limit=600,  # 600 actions per minute = 10 per second = 0.1s between actions
            budget=10,
            action_whitelist=["action1", "action2", "action3"]
        )
    
    def test_initialization(self):
        """Test that AgentSafeguards initializes correctly."""
        self.assertEqual(self.safeguards.rate_limit, 600)
        self.assertEqual(self.safeguards.budget, 10)
        self.assertEqual(self.safeguards.current_balance, 10)
        self.assertEqual(
            self.safeguards.action_whitelist,
            ["action1", "action2", "action3"]
        )
    
    def test_allowed_action(self):
        """Test executing an allowed action."""
        try:
            self.safeguards.can_execute_action("action1")
            success = True
        except Exception:
            success = False
        
        self.assertTrue(success)
        self.assertEqual(self.safeguards.current_balance, 9)
    
    def test_disallowed_action(self):
        """Test that disallowed actions raise an exception."""
        with self.assertRaises(Exception) as context:
            self.safeguards.can_execute_action("forbidden_action")
        
        self.assertIn("not permitted", str(context.exception))
    
    def test_budget_depletion(self):
        """Test that budget is properly depleted."""
        initial_balance = self.safeguards.current_balance
        
        # Execute an action
        self.safeguards.can_execute_action("action1")
        
        self.assertEqual(
            self.safeguards.current_balance,
            initial_balance - 1
        )
    
    def test_budget_exhaustion(self):
        """Test that exhausted budget prevents actions."""
        # Exhaust the budget
        for i in range(10):
            self.safeguards.can_execute_action("action1")
            time.sleep(0.11)  # Delay for rate limit (0.1s minimum between actions)
        
        # Next action should fail due to budget
        with self.assertRaises(Exception) as context:
            time.sleep(0.11)
            self.safeguards.can_execute_action("action1")
        
        self.assertIn("Budget exhausted", str(context.exception))
    
    def test_refill_budget(self):
        """Test budget refill functionality."""
        # Deplete some budget
        self.safeguards.can_execute_action("action1")
        time.sleep(0.11)
        self.safeguards.can_execute_action("action1")
        time.sleep(0.11)
        
        self.assertEqual(self.safeguards.current_balance, 8)
        
        # Refill (but note it will cap at original budget of 10)
        self.safeguards.refill_budget(5)
        
        # Should be capped at 10, not 13
        self.assertEqual(self.safeguards.current_balance, 10)
    
    def test_refill_budget_cap(self):
        """Test that refill doesn't exceed original budget."""
        # Start with full budget
        self.safeguards.refill_budget(100)
        
        # Should cap at original budget
        self.assertEqual(self.safeguards.current_balance, 10)
    
    def test_emergency_stop(self):
        """Test emergency stop functionality."""
        self.assertEqual(self.safeguards.current_balance, 10)
        
        self.safeguards.emergency_stop()
        
        self.assertEqual(self.safeguards.current_balance, 0)
        
        # Should not be able to execute actions
        with self.assertRaises(Exception) as context:
            self.safeguards.can_execute_action("action1")
        
        self.assertIn("Budget exhausted", str(context.exception))
    
    def test_rate_limit(self):
        """Test rate limiting functionality."""
        # First action should succeed
        self.safeguards.can_execute_action("action1")
        
        # Immediate second action should fail (rate limit)
        with self.assertRaises(Exception) as context:
            self.safeguards.can_execute_action("action1")
        
        self.assertIn("Rate limit exceeded", str(context.exception))
    
    def test_rate_limit_with_delay(self):
        """Test that rate limit allows action after delay."""
        # First action
        self.safeguards.can_execute_action("action1")
        
        # Wait for rate limit window (0.1s for 600 actions/min)
        time.sleep(0.11)
        
        # Second action should succeed
        try:
            self.safeguards.can_execute_action("action1")
            success = True
        except Exception:
            success = False
        
        self.assertTrue(success)
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        results = {"success": 0, "error": 0}
        lock = threading.Lock()
        
        def execute_action(delay):
            try:
                time.sleep(delay)  # Stagger threads
                self.safeguards.can_execute_action("action1")
                with lock:
                    results["success"] += 1
            except Exception:
                with lock:
                    results["error"] += 1
        
        # Create multiple threads with staggered delays
        threads = []
        for i in range(5):
            t = threading.Thread(target=execute_action, args=(i * 0.11,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have some successes and some rate limit errors
        self.assertGreater(results["success"], 0)
        self.assertEqual(results["success"] + results["error"], 5)
    
    def test_monitor(self):
        """Test monitoring functionality."""
        # Should not raise an exception
        try:
            self.safeguards.monitor()
            success = True
        except Exception:
            success = False
        
        self.assertTrue(success)


class TestAgentSafeguardsEdgeCases(unittest.TestCase):
    """Test edge cases for AgentSafeguards."""
    
    def test_zero_budget(self):
        """Test safeguards with zero budget."""
        safeguards = AgentSafeguards(
            rate_limit=10,
            budget=0,
            action_whitelist=["action1"]
        )
        
        with self.assertRaises(Exception) as context:
            safeguards.can_execute_action("action1")
        
        self.assertIn("Budget exhausted", str(context.exception))
    
    def test_empty_whitelist(self):
        """Test safeguards with empty whitelist."""
        safeguards = AgentSafeguards(
            rate_limit=10,
            budget=10,
            action_whitelist=[]
        )
        
        with self.assertRaises(Exception) as context:
            safeguards.can_execute_action("any_action")
        
        self.assertIn("not permitted", str(context.exception))
    
    def test_high_rate_limit(self):
        """Test with very high rate limit."""
        safeguards = AgentSafeguards(
            rate_limit=1000,
            budget=100,
            action_whitelist=["action1"]
        )
        
        # Should allow rapid actions (1000 per min = ~16 per second = 0.06s between actions)
        for i in range(10):
            safeguards.can_execute_action("action1")
            if i < 9:  # Don't sleep after the last action
                time.sleep(0.07)  # Small delay for rate limit
        
        self.assertEqual(safeguards.current_balance, 90)


def run_tests():
    """Run all tests and display results."""
    print("=" * 60)
    print("Running AgentSafeguards Tests")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAgentSafeguards))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentSafeguardsEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
