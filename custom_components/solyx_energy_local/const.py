"""Constants for the Solyx Energy Local integration."""

DOMAIN = "solyx_energy_local"

# The Sensorbox reads the Nymo every 30 seconds, so polling faster gains nothing.
DATA_INTERVAL_SECONDS = 30

# The power of direct mode until the user sets one, as the Sensorbox uses by default
DEFAULT_DIRECT_PERCENT = 50

# Config entry keys; the host, port and access token use the Home Assistant constants
CONF_CERT_SHA256 = "cert_sha256"

# mDNS TXT record key that holds the device ID
DISCOVERY_DEVICE_ID = "deviceId"
