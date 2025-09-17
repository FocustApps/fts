"""
Storage package for Fenrir authentication token management.

This package provides a generic storage interface for authentication tokens
that can be implemented across multiple cloud storage providers.
"""

from .base import StorageProvider, StorageError
from .local_filesystem import LocalFileSystemProvider
from .aws_s3 import AWSS3Provider
from .azure_blob import AzureBlobProvider
from .storage_service import StorageService, create_storage_service, DEFAULT_CONFIGS

__all__ = [
    # Base classes and exceptions
    "StorageProvider",
    "StorageError",
    # Storage provider implementations
    "LocalFileSystemProvider",
    "AWSS3Provider",
    "AzureBlobProvider",
    # Storage service
    "StorageService",
    "create_storage_service",
    "DEFAULT_CONFIGS",
]
