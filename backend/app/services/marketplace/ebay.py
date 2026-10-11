"""
eBay marketplace integration.
"""
from typing import Dict, Any
from app.services.marketplace.base import MarketplaceService


class EbayService(MarketplaceService):
    """eBay marketplace integration."""
    
    async def authenticate(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate with eBay using OAuth.
        
        Args:
            auth_data: OAuth authorization code
            
        Returns:
            Access token and refresh token
        """
        # TODO: Implement actual eBay OAuth flow
        # Would use eBay API credentials from config
        
        return {
            "connected": False,
            "status": "needs_keys",
            "access_token": None,
            "refresh_token": None,
            "error": "eBay is not connected. API keys are not configured.",
        }
    
    async def publish_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a listing to eBay.
        
        Args:
            listing_data: Product information
            
        Returns:
            eBay listing URL and ID
        """
        # TODO: Implement actual eBay API call
        # Would use Trading API or Inventory API
        
        return {
            "external_id": None,
            "url": None,
            "status": "needs_keys",
            "error": "eBay publishing is not connected.",
        }
    
    async def fetch_messages(self) -> list:
        """
        Fetch messages from eBay.
        
        Returns:
            List of eBay messages
        """
        # TODO: Implement actual eBay message fetching
        return []
    
    async def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a message to eBay user.
        
        Args:
            recipient: eBay user ID
            message: Message content
            
        Returns:
            Success status
        """
        # Messaging is not connected.
        return False
