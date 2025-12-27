"""Persistence module for Ink application.

This module provides settings and state persistence using Qt's QSettings
and other platform-native storage mechanisms.

Exports:
    AppSettings: Application settings manager using QSettings.
    PanelSettingsStore: Panel layout state persistence using QSettings.
"""

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.infrastructure.persistence.panel_settings_store import PanelSettingsStore

__all__ = ["AppSettings", "PanelSettingsStore"]
