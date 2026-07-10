"""Shared error types for the DevOps career agent."""

from __future__ import annotations


class CareerAgentError(Exception):
    """Base class for feature-specific errors."""


class BoundaryViolationError(CareerAgentError):
    """Raised when a request crosses the HR or performance boundary."""

    def __init__(self, message: str, category: str = "boundary") -> None:
        super().__init__(message)
        self.category = category


class ConfigurationError(CareerAgentError):
    """Raised when runtime configuration is invalid."""


class DataNotFoundError(CareerAgentError):
    """Raised when a requested record is missing."""


class UnsupportedTopicError(CareerAgentError):
    """Raised when topic guidance is requested for an unsupported topic."""


class ValidationError(CareerAgentError):
    """Raised when domain-specific validation fails."""

