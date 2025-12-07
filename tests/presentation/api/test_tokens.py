"""Tests for the tokens API router.

Tests GET /api/tokens and GET /api/tokens/{token_symbol} endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rwa_aggregator.domain.entities.token import Token, TokenCategory
from app.rwa_aggregator.presentation.api.tokens import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the tokens router."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_tokens() -> list[Token]:
    """Create mock tokens for testing."""
    return [
        Token(
            id=1,
            symbol="USDY",
            name="Ondo US Dollar Yield",
            category=TokenCategory.TBILL,
            issuer="Ondo Finance",
            chain="ethereum",
            contract_address="0x96F6eF951840721AdBF46Ac996b59E0235CB985C",
            is_active=True,
        ),
        Token(
            id=2,
            symbol="OUSG",
            name="Ondo Short-Term US Gov Treasuries",
            category=TokenCategory.TBILL,
            issuer="Ondo Finance",
            chain="ethereum",
            contract_address="0x1B19C19393e2d034D8Ff31ff34c81252FcBbee92",
            is_active=True,
        ),
        Token(
            id=3,
            symbol="BENJI",
            name="Franklin OnChain US Gov Money Fund",
            category=TokenCategory.TBILL,
            issuer="Franklin Templeton",
            chain="polygon",
            contract_address="0xBDa5B1f690Ba3bD1B1efAD5F9Ae1c63D6CcC10cf",
            is_active=True,
        ),
    ]


class TestListTokens:
    """Tests for GET /api/tokens."""

    def test_list_tokens_success(
        self,
        client: TestClient,
        mock_tokens: list[Token],
    ) -> None:
        """Test successful token listing."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_all_active.return_value = mock_tokens
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert len(data["tokens"]) == 3
            assert data["tokens"][0]["symbol"] == "USDY"
            assert data["tokens"][1]["symbol"] == "OUSG"
            assert data["tokens"][2]["symbol"] == "BENJI"

    def test_list_tokens_empty(self, client: TestClient) -> None:
        """Test empty list when no tokens exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_all_active.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["tokens"] == []

    def test_list_tokens_by_category(
        self,
        client: TestClient,
        mock_tokens: list[Token],
    ) -> None:
        """Test filtering tokens by category."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            # Return all tbill tokens
            mock_repo.get_by_category.return_value = mock_tokens
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens?category=tbill")

            assert response.status_code == 200
            mock_repo.get_by_category.assert_called_once_with(TokenCategory.TBILL)

    def test_list_tokens_invalid_category(self, client: TestClient) -> None:
        """Test filtering with invalid category returns empty list."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens?category=invalid_category")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["tokens"] == []


class TestGetToken:
    """Tests for GET /api/tokens/{token_symbol}."""

    def test_get_token_success(
        self,
        client: TestClient,
        mock_tokens: list[Token],
    ) -> None:
        """Test successful token retrieval."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_symbol.return_value = mock_tokens[0]
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens/USDY")

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "USDY"
            assert data["name"] == "Ondo US Dollar Yield"
            assert data["category"] == "tbill"
            assert data["issuer"] == "Ondo Finance"

    def test_get_token_not_found(self, client: TestClient) -> None:
        """Test 404 response when token doesn't exist."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_symbol.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens/INVALID")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_token_case_insensitive(
        self,
        client: TestClient,
        mock_tokens: list[Token],
    ) -> None:
        """Test that token symbol is case-insensitive."""
        with patch(
            "app.rwa_aggregator.presentation.api.tokens.SqlTokenRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_symbol.return_value = mock_tokens[0]
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/tokens/usdy")

            assert response.status_code == 200
            mock_repo.get_by_symbol.assert_called_once_with("USDY")
