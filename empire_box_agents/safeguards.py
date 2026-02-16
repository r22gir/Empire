import time
import threading

class AgentSafeguards:
    def __init__(self, rate_limit, budget, action_whitelist):
        self.rate_limit = rate_limit  # actions per minute
        self.budget = budget  # total budget for actions
        self.action_whitelist = action_whitelist  # list of allowed actions
        self.current_balance = budget
        self.lock = threading.Lock()
        self.last_action_time = time.time()

    def can_execute_action(self, action):
        if action not in self.action_whitelist:
            raise Exception("Action not permitted.")
        
        with self.lock:
            current_time = time.time()
            time_since_last_action = current_time - self.last_action_time

            if time_since_last_action < 60 / self.rate_limit:
                raise Exception("Rate limit exceeded. Please wait.")
            
            if self.current_balance <= 0:
                raise Exception("Budget exhausted.")
            
            # Update state for the next action
            self.last_action_time = current_time
            self.current_balance -= 1  # decrement budget for action

    def refill_budget(self, amount):
        with self.lock:
            self.current_balance += amount
            if self.current_balance > self.budget:
                self.current_balance = self.budget

    def emergency_stop(self):
        with self.lock:
            self.current_balance = 0
            print("Emergency stop activated! Budget set to zero.")

    def monitor(self):
        # Place logic to monitor agent performance and environment
        print("Monitoring agent performance...")

# Example usage:
if __name__ == "__main__":
    safeguards = AgentSafeguards(rate_limit=5, budget=10, action_whitelist=["action1", "action2"])

    try:
        safeguards.can_execute_action("action1")
        # Execute the action
    except Exception as e:
        print(e)
