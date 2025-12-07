"""Application-layer exceptions for use case error handling.

These exceptions represent business logic errors that can occur during
use case execution. They are designed to be caught and mapped to
appropriate HTTP responses by the presentation layer.
"""


class ApplicationError(Exception):
    """Base class for all application-layer exceptions."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class TokenNotFoundError(ApplicationError):
    """Raised when a requested token does not exist."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            message=f"Token with symbol '{symbol}' not found",
            code="TOKEN_NOT_FOUND"
        )
        self.symbol = symbol


class VenueNotFoundError(ApplicationError):
    """Raised when a requested venue does not exist."""

    def __init__(self, identifier: str | int) -> None:
        super().__init__(
            message=f"Venue '{identifier}' not found",
            code="VENUE_NOT_FOUND"
        )
        self.identifier = identifier


class AlertNotFoundError(ApplicationError):
    """Raised when a requested alert does not exist."""

    def __init__(self, alert_id: int) -> None:
        super().__init__(
            message=f"Alert with ID {alert_id} not found",
            code="ALERT_NOT_FOUND"
        )
        self.alert_id = alert_id


class AlertAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a duplicate alert."""

    def __init__(self, email: str, token_symbol: str) -> None:
        super().__init__(
            message=f"Alert for {token_symbol} already exists for {email}",
            code="ALERT_ALREADY_EXISTS"
        )
        self.email = email
        self.token_symbol = token_symbol


class InvalidEmailError(ApplicationError):
    """Raised when an email address fails validation."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"Invalid email address: {email}",
            code="INVALID_EMAIL"
        )
        self.email = email


class NoPriceDataError(ApplicationError):
    """Raised when no price data is available for a token."""

    def __init__(self, token_symbol: str) -> None:
        super().__init__(
            message=f"No price data available for token '{token_symbol}'",
            code="NO_PRICE_DATA"
        )
        self.token_symbol = token_symbol


class TokenNotTradableError(ApplicationError):
    """Raised when an operation requires a tradable token but a NAV-only token is provided.

    NAV-only tokens (like OUSG, BENJI) don't have active trading pairs on exchanges,
    so operations like creating spread alerts are not supported for them.
    """

    def __init__(self, token_symbol: str) -> None:
        super().__init__(
            message=(
                f"Token '{token_symbol}' is a NAV-only asset without active trading pairs. "
                f"Spread alerts are only available for tokens with live bid/ask data."
            ),
            code="TOKEN_NOT_TRADABLE"
        )
        self.token_symbol = token_symbol
