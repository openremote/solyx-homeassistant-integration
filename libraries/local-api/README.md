# Solyx Energy local API

Async HTTP client for the local API of the Solyx Energy Sensorbox, on the home
network. It reads the device info and status of the Nymo and sets its operating
mode.

The Sensorbox uses a self-signed certificate, which the client pins by its
SHA-256 fingerprint; the access token is only sent once the fingerprint matched.
The token and fingerprint are shown in the Solyx Energy app.

The Solyx Energy Local Home Assistant integration uses this package. The cloud
API has its own package, `solyx-energy-api-client`.
