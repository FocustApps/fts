"""
Base class for all database models.

This module provides the declarative base that all SQLAlchemy models inherit from.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


__all__ = ["Base"]
