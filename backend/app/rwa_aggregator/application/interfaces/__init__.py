# Ports for external integrations (PriceFeed, EmailSender)

from .price_feed import NormalizedQuote, PriceFeed

__all__ = [
    "NormalizedQuote",
    "PriceFeed",
]
