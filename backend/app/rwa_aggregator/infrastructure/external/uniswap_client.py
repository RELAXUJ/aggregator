"""Uniswap Subgraph client for fetching DEX price quotes via The Graph.

Uses Uniswap V3 subgraph for pool data and price calculations.
GraphQL endpoint: https://api.studio.thegraph.com/query/48211/uniswap-v3/latest
Rate limit: ~1000 queries/minute.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from backend.app.rwa_aggregator.application.interfaces.price_feed import (
    NormalizedQuote,
    PriceFeed,
)

logger = logging.getLogger(__name__)

# Uniswap V3 subgraph endpoints by network
UNISWAP_SUBGRAPH_URLS = {
    "mainnet": "https://api.studio.thegraph.com/query/48211/uniswap-v3-mainnet/version/latest",
    "arbitrum": "https://api.studio.thegraph.com/query/48211/uniswap-v3-arbitrum/version/latest",
    "polygon": "https://api.studio.thegraph.com/query/48211/uniswap-v3-polygon/version/latest",
    "optimism": "https://api.studio.thegraph.com/query/48211/uniswap-v3-optimism/version/latest",
}

# Mapping from token symbols to Ethereum mainnet contract addresses (lowercase)
# These are used to look up pools on Uniswap
TOKEN_ADDRESSES: dict[str, str] = {
    # Major tokens
    "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    "ETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # Maps to WETH
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "WBTC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
    # RWA tokens on Ethereum mainnet
    "PAXG": "0x45804880de22913dafe09f4980848ece6ecbaf78",  # Paxos Gold
    "ONDO": "0xfaba6f8e4a5e8ab82f62fe7c39859fa577269be3",  # Ondo Finance
    "USDY": "0x96f6ef951840721adbf46ac996b59e0235cb985c",  # Ondo USDY (verify address)
    # Stablecoins paired with USD for reference
    "FRAX": "0x853d955acef822db058eb8505911ed77f175b99e",
}

# Mapping of token symbols to their most liquid pools (pool addresses)
# These are pre-configured pools for common pairs
POOL_ADDRESSES: dict[str, str] = {
    # Format: "TOKEN-QUOTE" -> pool_address
    "WETH-USDC": "0x8ad599c3a0ff1de082011efddc58f1908762f2f7",  # USDC/ETH 0.3%
    "WBTC-USDC": "0x99ac8ca7087fa4a2a1fb6357269965a2014abc35",  # WBTC/USDC 0.3%
    "PAXG-WETH": "0x8cfe11dc2f46e5d9e3ffa3d86a8d8bd93bc15d8e",  # PAXG/WETH (verify)
}

# Default spread estimate for DEX (in basis points)
# DEX quotes are mid-prices; we estimate spread based on pool fee tier
FEE_TIER_SPREAD_BPS = {
    100: 2,     # 0.01% fee tier -> ~2 bps spread
    500: 10,    # 0.05% fee tier -> ~10 bps spread
    3000: 60,   # 0.3% fee tier -> ~60 bps spread
    10000: 200, # 1% fee tier -> ~200 bps spread
}

DEFAULT_TIMEOUT_SECONDS = 15.0


class UniswapClient(PriceFeed):
    """Uniswap V3 Subgraph client implementing the PriceFeed interface.

    This client queries The Graph's Uniswap V3 subgraph for pool data
    and calculates price quotes from liquidity pool prices.

    Note: DEX prices are mid-prices derived from pool state. Actual execution
    prices depend on trade size and current liquidity distribution.

    Attributes:
        _client: httpx AsyncClient for GraphQL requests.
        _subgraph_url: The Graph endpoint URL.
        _network: Network name (mainnet, arbitrum, etc.).
    """

    def __init__(
        self,
        network: str = "mainnet",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the Uniswap client.

        Args:
            network: Network to query (mainnet, arbitrum, polygon, optimism).
            timeout: HTTP request timeout in seconds.
        """
        self._network = network.lower()
        self._subgraph_url = UNISWAP_SUBGRAPH_URLS.get(
            self._network,
            UNISWAP_SUBGRAPH_URLS["mainnet"],
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    @property
    def venue_name(self) -> str:
        """Return the venue name."""
        return f"Uniswap V3 ({self._network.capitalize()})"

    def supports_token(self, token_symbol: str) -> bool:
        """Check if Uniswap has a known pool for this token.

        Args:
            token_symbol: Normalized token symbol.

        Returns:
            True if the token has a known address for pool lookup.
        """
        return token_symbol.upper() in TOKEN_ADDRESSES

    async def fetch_quote(self, token_symbol: str) -> Optional[NormalizedQuote]:
        """Fetch a price quote from Uniswap for the given token.

        Queries the subgraph for pool data and calculates mid-price.
        For DEX, bid/ask are estimated from mid-price using pool fee tier.

        Args:
            token_symbol: Normalized token symbol (e.g., "ETH", "PAXG").

        Returns:
            NormalizedQuote with estimated bid/ask, or None if unavailable.
        """
        symbol_upper = token_symbol.upper()
        token_address = TOKEN_ADDRESSES.get(symbol_upper)

        if not token_address:
            logger.debug(f"Uniswap: No known address for token: {token_symbol}")
            return None

        try:
            # Query pools where this token is either token0 or token1
            # We look for USD-denominated pools (USDC, USDT, DAI) for price
            pool_data = await self._query_token_pools(token_address)

            if not pool_data:
                logger.warning(f"No Uniswap pools found for {token_symbol}")
                return None

            # Calculate price from pool data
            price_info = self._calculate_price_from_pools(pool_data, token_address)

            if not price_info:
                logger.warning(f"Could not calculate price for {token_symbol}")
                return None

            mid_price = price_info["price"]
            volume_24h = price_info.get("volume_usd")
            fee_tier = price_info.get("fee_tier", 3000)

            # Estimate bid/ask spread based on fee tier
            spread_bps = FEE_TIER_SPREAD_BPS.get(fee_tier, 60)
            half_spread = mid_price * Decimal(spread_bps) / Decimal("20000")

            bid_price = mid_price - half_spread
            ask_price = mid_price + half_spread

            return NormalizedQuote(
                venue_name=self.venue_name,
                token_symbol=symbol_upper,
                bid=bid_price,
                ask=ask_price,
                volume_24h=Decimal(str(volume_24h)) if volume_24h else None,
                timestamp=datetime.now(timezone.utc),
            )

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching Uniswap quote for {token_symbol}")
            return None
        except Exception as e:
            logger.exception(f"Error fetching Uniswap quote for {token_symbol}: {e}")
            return None

    async def _query_token_pools(self, token_address: str) -> Optional[list[dict]]:
        """Query subgraph for pools containing the token.

        Args:
            token_address: Ethereum address of the token (lowercase).

        Returns:
            List of pool data dictionaries, or None on error.
        """
        # GraphQL query to find pools where this token trades against stablecoins
        query = """
        query GetTokenPools($token: String!) {
            poolsAsToken0: pools(
                first: 5
                where: {
                    token0: $token
                    token1_in: [
                        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                        "0xdac17f958d2ee523a2206206994597c13d831ec7",
                        "0x6b175474e89094c44da98b954eedeac495271d0f"
                    ]
                }
                orderBy: totalValueLockedUSD
                orderDirection: desc
            ) {
                id
                token0 { id symbol decimals }
                token1 { id symbol decimals }
                feeTier
                liquidity
                token0Price
                token1Price
                volumeUSD
                totalValueLockedUSD
            }
            poolsAsToken1: pools(
                first: 5
                where: {
                    token1: $token
                    token0_in: [
                        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                        "0xdac17f958d2ee523a2206206994597c13d831ec7",
                        "0x6b175474e89094c44da98b954eedeac495271d0f"
                    ]
                }
                orderBy: totalValueLockedUSD
                orderDirection: desc
            ) {
                id
                token0 { id symbol decimals }
                token1 { id symbol decimals }
                feeTier
                liquidity
                token0Price
                token1Price
                volumeUSD
                totalValueLockedUSD
            }
        }
        """

        payload = {
            "query": query,
            "variables": {"token": token_address.lower()},
        }

        response = await self._client.post(self._subgraph_url, json=payload)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            return None

        result = data.get("data", {})
        pools = result.get("poolsAsToken0", []) + result.get("poolsAsToken1", [])

        return pools if pools else None

    def _calculate_price_from_pools(
        self, pools: list[dict], token_address: str
    ) -> Optional[dict]:
        """Calculate USD price from pool data.

        Uses the highest TVL pool for price reference.

        Args:
            pools: List of pool data from subgraph.
            token_address: Address of the token we want price for.

        Returns:
            Dictionary with 'price', 'volume_usd', and 'fee_tier'.
        """
        if not pools:
            return None

        # Sort by TVL and use the most liquid pool
        pools_sorted = sorted(
            pools,
            key=lambda p: float(p.get("totalValueLockedUSD", "0")),
            reverse=True,
        )

        best_pool = pools_sorted[0]
        token0_id = best_pool["token0"]["id"].lower()
        token1_id = best_pool["token1"]["id"].lower()

        # Determine if our token is token0 or token1
        if token0_id == token_address.lower():
            # Our token is token0, price in terms of token1 (stablecoin)
            price_str = best_pool["token1Price"]
        else:
            # Our token is token1, price in terms of token0 (stablecoin)
            price_str = best_pool["token0Price"]

        try:
            price = Decimal(price_str)
            volume_usd = float(best_pool.get("volumeUSD", "0"))
            fee_tier = int(best_pool.get("feeTier", "3000"))

            return {
                "price": price,
                "volume_usd": volume_usd,
                "fee_tier": fee_tier,
            }
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing pool price: {e}")
            return None

    async def fetch_pool_details(self, pool_address: str) -> Optional[dict]:
        """Fetch detailed information about a specific pool.

        Args:
            pool_address: Ethereum address of the Uniswap pool.

        Returns:
            Dictionary with pool details, or None on error.
        """
        query = """
        query GetPool($pool: String!) {
            pool(id: $pool) {
                id
                token0 { id symbol name decimals }
                token1 { id symbol name decimals }
                feeTier
                liquidity
                sqrtPrice
                tick
                token0Price
                token1Price
                volumeUSD
                feesUSD
                totalValueLockedUSD
                txCount
            }
        }
        """

        try:
            payload = {
                "query": query,
                "variables": {"pool": pool_address.lower()},
            }

            response = await self._client.post(self._subgraph_url, json=payload)
            response.raise_for_status()
            data = response.json()

            return data.get("data", {}).get("pool")

        except Exception as e:
            logger.error(f"Error fetching pool details for {pool_address}: {e}")
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "UniswapClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
