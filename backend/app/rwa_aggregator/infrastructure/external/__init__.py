# External clients - Kraken, Coinbase, Uniswap, Postmark

from .coinbase_client import CoinbaseClient
from .kraken_client import KrakenClient
from .price_feed_registry import PriceFeedRegistry, create_default_registry
from .uniswap_client import UniswapClient

__all__ = [
    "CoinbaseClient",
    "KrakenClient",
    "PriceFeedRegistry",
    "UniswapClient",
    "create_default_registry",
]
