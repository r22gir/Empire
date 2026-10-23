"""Max client-invoice path: Square share-link → existing PDF → Outlook draft.

Nothing in this package sends mail, SMS, or a Square invoice to the client.
Rafael sends himself.
"""
from app.services.client_invoice.produce import produce_client_invoice

__all__ = ["produce_client_invoice"]
