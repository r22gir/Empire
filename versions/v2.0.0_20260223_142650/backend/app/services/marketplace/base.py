"""
Base class for marketplace integrations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class MarketplaceService(ABC):
    """Abstract base class for marketplace integrations."""
    
    def __init__(self, credentials: Optional[Dict[str, Any]] = None):
        """
        Initialize marketplace service.
        
        Args:
            credentials: API credentials for the marketplace
        """
        self.credentials = credentials
    
    @abstractmethod
    async def authenticate(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate with the marketplace.
        
        Args:
            auth_data: Authentication data (OAuth code, API keys, etc.)
            
        Returns:
            Credentials to store
        """
        pass
    
    @abstractmethod
    async def publish_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a listing to the marketplace.
        
        Args:
            listing_data: Listing information
            
        Returns:
            Result with listing URL and external ID
        """
        pass
    
    @abstractmethod
    async def fetch_messages(self) -> list:
        """
        Fetch messages from the marketplace.
        
        Returns:
            List of messages
        """
        pass
    
    @abstractmethod
    async def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a message through the marketplace.
        
        Args:
            recipient: Recipient identifier
            message: Message content
            
        Returns:
            Success status
        """
        pass
