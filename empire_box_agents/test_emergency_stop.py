"""
Unit tests for the EmergencyStop system.

Run with: python test_emergency_stop.py
"""

import unittest
from emergency_stop import EmergencyStop


class TestEmergencyStop(unittest.TestCase):
    """Test cases for EmergencyStop functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.emergency_stop = EmergencyStop()
    
    def test_initialization(self):
        """Test that EmergencyStop initializes correctly."""
        self.assertFalse(self.emergency_stop.state_saved)
        self.assertTrue(self.emergency_stop.is_running)
        self.assertFalse(self.emergency_stop.manual_triggered)
        self.assertFalse(self.emergency_stop.admin_alerted)
    
    def test_manual_trigger(self):
        """Test manual emergency stop trigger."""
        self.emergency_stop.manual_trigger()
        
        # Verify state
        self.assertTrue(self.emergency_stop.manual_triggered)
        self.assertFalse(self.emergency_stop.is_running)
        self.assertTrue(self.emergency_stop.state_saved)
        self.assertTrue(self.emergency_stop.admin_alerted)
    
    def test_auto_trigger_no_failure(self):
        """Test auto trigger when no failure conditions exist."""
        # Default detect_failure_conditions returns False
        self.emergency_stop.auto_trigger()
        
        # Should not trigger
        self.assertTrue(self.emergency_stop.is_running)
        self.assertFalse(self.emergency_stop.state_saved)
    
    def test_auto_trigger_with_failure(self):
        """Test auto trigger with failure condition."""
        # Mock failure detection
        self.emergency_stop.detect_failure_conditions = lambda: True
        
        self.emergency_stop.auto_trigger()
        
        # Should trigger
        self.assertFalse(self.emergency_stop.is_running)
        self.assertTrue(self.emergency_stop.state_saved)
        self.assertTrue(self.emergency_stop.admin_alerted)
    
    def test_save_state(self):
        """Test state saving functionality."""
        self.assertFalse(self.emergency_stop.state_saved)
        
        self.emergency_stop.save_state()
        
        self.assertTrue(self.emergency_stop.state_saved)
    
    def test_kill_agent(self):
        """Test agent killing functionality."""
        self.assertTrue(self.emergency_stop.is_running)
        
        self.emergency_stop.kill_agent()
        
        self.assertFalse(self.emergency_stop.is_running)
    
    def test_alert_admin(self):
        """Test admin alerting functionality."""
        self.assertFalse(self.emergency_stop.admin_alerted)
        
        self.emergency_stop.alert_admin("Test message")
        
        self.assertTrue(self.emergency_stop.admin_alerted)
    
    def test_multiple_manual_triggers(self):
        """Test that multiple manual triggers don't cause issues."""
        self.emergency_stop.manual_trigger()
        first_state = self.emergency_stop.state_saved
        
        # Trigger again
        self.emergency_stop.manual_trigger()
        
        # State should remain consistent
        self.assertFalse(self.emergency_stop.is_running)
        self.assertTrue(self.emergency_stop.manual_triggered)
        self.assertTrue(first_state)
    
    def test_state_consistency(self):
        """Test that state remains consistent after emergency stop."""
        # Trigger emergency stop
        self.emergency_stop.manual_trigger()
        
        # Verify all related states
        self.assertFalse(self.emergency_stop.is_running)
        self.assertTrue(self.emergency_stop.state_saved)
        self.assertTrue(self.emergency_stop.manual_triggered)
        self.assertTrue(self.emergency_stop.admin_alerted)


class TestEmergencyStopCustom(unittest.TestCase):
    """Test cases for custom EmergencyStop implementations."""
    
    def test_custom_failure_detection(self):
        """Test custom failure detection logic."""
        class CustomEmergencyStop(EmergencyStop):
            def __init__(self):
                super().__init__()
                self.failure_threshold = 5
                self.error_count = 0
            
            def detect_failure_conditions(self):
                return self.error_count >= self.failure_threshold
        
        custom_stop = CustomEmergencyStop()
        
        # Initially no failure
        self.assertFalse(custom_stop.detect_failure_conditions())
        
        # Simulate errors
        custom_stop.error_count = 6
        
        # Now should detect failure
        self.assertTrue(custom_stop.detect_failure_conditions())
        
        # Auto trigger should work
        custom_stop.auto_trigger()
        self.assertFalse(custom_stop.is_running)


def run_tests():
    """Run all tests and display results."""
    print("=" * 60)
    print("Running EmergencyStop Tests")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestEmergencyStop))
    suite.addTests(loader.loadTestsFromTestCase(TestEmergencyStopCustom))
    
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
