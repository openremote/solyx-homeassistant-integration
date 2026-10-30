"""Exceptions raised by the Solyx Energy local API client."""


class SolyxEnergyError(Exception):
    """Base error for the Solyx Energy local API client."""


class SolyxEnergyAuthError(SolyxEnergyError):
    """The Sensorbox rejected the access token."""


class SolyxEnergyCertificateError(SolyxEnergyError):
    """The Sensorbox presented a certificate that does not match the pinned fingerprint."""


class SolyxEnergyDataError(SolyxEnergyError):
    """The Sensorbox could not be reached or sent an invalid response."""


class SolyxEnergyWriteError(SolyxEnergyError):
    """The Sensorbox did not accept a change."""


class SolyxEnergyLocalControlDisabledError(SolyxEnergyWriteError):
    """A change was refused because local control is turned off."""
