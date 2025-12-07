"""Abstract repository interface for Token entities."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.token import Token, TokenCategory


class TokenRepository(ABC):
    """Abstract repository for Token persistence operations.

    Implementations should handle database-specific concerns while
    returning domain entities. All methods are async to support
    non-blocking I/O in the infrastructure layer.
    """

    @abstractmethod
    async def get_by_id(self, token_id: int) -> Optional[Token]:
        """Retrieve a token by its database ID.

        Args:
            token_id: The unique identifier of the token.

        Returns:
            The Token entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_symbol(self, symbol: str) -> Optional[Token]:
        """Retrieve a token by its ticker symbol.

        Args:
            symbol: The token symbol (e.g., "USDY", "BENJI").

        Returns:
            The Token entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_all_active(self) -> List[Token]:
        """Retrieve all tokens that are currently active.

        Returns:
            List of Token entities where is_active is True.
        """
        pass

    @abstractmethod
    async def get_by_category(self, category: TokenCategory) -> List[Token]:
        """Retrieve all active tokens in a specific category.

        Args:
            category: The TokenCategory to filter by.

        Returns:
            List of active Token entities in the specified category.
        """
        pass

    @abstractmethod
    async def save(self, token: Token) -> Token:
        """Persist a token entity.

        For new tokens (id is None), this creates a new record.
        For existing tokens, this updates the existing record.

        Args:
            token: The Token entity to save.

        Returns:
            The saved Token entity with its ID populated.
        """
        pass
