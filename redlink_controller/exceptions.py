class RedlinkError(Exception):
    """Base exception for Redlink controller errors."""


class LoginError(RedlinkError):
    """Raised when the login flow fails."""


class RequestError(RedlinkError):
    """Raised for unexpected HTTP responses."""


class EndpointNotConfigured(RedlinkError):
    """Raised when an endpoint needed for an action is not configured."""
