"""
Database-related enumerations.

This module contains enums used across the database models.
"""

from enum import StrEnum


class SystemEnum(StrEnum):
    """Enumeration of supported systems for email processing."""

    MINER_OCR = "miner_ocr"
    TRUE_SOURCE_OCR = "true_source_ocr"

    @staticmethod
    def get_valid_systems():
        return [system.value for system in SystemEnum]

    @staticmethod
    def is_valid_system(system: str):
        return system in SystemEnum.get_valid_systems()


__all__ = ["SystemEnum"]
