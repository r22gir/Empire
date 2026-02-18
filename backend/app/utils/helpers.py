"""
Common utility functions.
"""
from typing import Optional
import re


def generate_marketforge_email(name: str, email: str) -> str:
    """
    Generate a unique @marketforge.app email address.
    
    Args:
        name: User's name
        email: User's primary email
        
    Returns:
        Generated marketforge email address
    """
    # Extract username from email
    username = email.split("@")[0]
    # Clean and normalize
    username = re.sub(r'[^a-zA-Z0-9]', '', username.lower())
    # Add random suffix if needed for uniqueness
    return f"{username}@marketforge.app"


def get_token_limit(tier: str) -> int:
    """
    Get token limit for a subscription tier.
    
    Args:
        tier: Subscription tier name
        
    Returns:
        Monthly token limit
    """
    limits = {
        "free": 100,
        "lite": 1000,
        "pro": 10000,
        "empire": 100000
    }
    return limits.get(tier, 100)


def calculate_percent_used(used: int, limit: int) -> float:
    """Calculate percentage of tokens used."""
    if limit == 0:
        return 0.0
    return round((used / limit) * 100, 2)
