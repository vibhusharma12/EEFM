"""Errors raised by the ML pipeline. Messages are safe to show to API clients."""
from __future__ import annotations


class MLError(Exception):
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InsufficientDataError(MLError):
    """Not enough clean history to build features, train, or evaluate."""

    status_code = 422


class ModelTrainingError(MLError):
    """Training or evaluation failed for a reason other than missing data."""

    status_code = 500
