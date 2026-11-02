"""Deterministic, network-free assessment of the authoritative Golden Pairs."""

from .engine import VerificationUnavailable, verify, validate_source

__all__ = ["VerificationUnavailable", "verify", "validate_source"]
