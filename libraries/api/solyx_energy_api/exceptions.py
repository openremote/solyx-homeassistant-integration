"""Exceptions raised by the Solyx Energy API client."""


class SolyxEnergyError(Exception):
    """Base error for the Solyx Energy API client."""


class SolyxEnergyAuthError(SolyxEnergyError):
    """Error related to authentication or authorization failures."""


class SolyxEnergyTokenError(SolyxEnergyError):
    """Error during access token retrieval."""


class SolyxEnergyDataError(SolyxEnergyError):
    """Error during data retrieval."""


class SolyxEnergyWriteError(SolyxEnergyError):
    """Error when pushing a value."""
