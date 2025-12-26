"""Persistence module for Ink application.

This module provides settings and state persistence using Qt's QSettings
and other platform-native storage mechanisms.

Exports:
    AppSettings: Application settings manager using QSettings.
"""

from ink.infrastructure.persistence.app_settings import AppSettings

__all__ = ["AppSettings"]
