# Home Assistant integration for Solyx Energy devices

Home Assistant integration for controlling and gaining insight in Solyx Energy devices

## Solyx Energy Local

`custom_components/solyx_energy_local` connects to the Nymo over the home
network instead of the Solyx Energy cloud. It shows the same sensors as the
cloud integration, read from the local API of the Sensorbox.

Requirements:
- Sensorbox firmware with the local API.
- The access token and certificate fingerprint, shown in the Solyx Energy app.

Home Assistant finds the Nymo on the network by itself (mDNS, `_solyx._tcp`)
and only asks for the access token and certificate fingerprint. It can also be
added by hand with its address, for example `solyx-a1b2c3.local`. The
certificate fingerprint pins the self-signed certificate of the Sensorbox; the
token is never sent to a device that presents another certificate.

Besides the sensors of the cloud integration, it can control the Nymo while
local control is turned on in the Solyx Energy app:

| Entity | Description |
|--------|-------------|
| Operating mode (`select`) | Normal, muted or direct; direct mode heats with 50 % of the boiler's power |

## Development

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ./libraries/api -e ./libraries/local-api
python -m pytest
```

The first command installs `homeassistant`, pytest utilities, `ruff`, and
`mypy`. The second installs both API packages from this repository in editable mode.

Lint and type-check before submitting:

```bash
ruff check .
mypy libraries/api/solyx_energy_api libraries/local-api/solyx_energy_local_api custom_components
```

The API package is published separately and is installed by Home Assistant
through the integration requirement in `manifest.json`.

### Running Home Assistant

`scripts/develop` starts Home Assistant on http://localhost:8123 with the
integrations from this repository, using the configuration in `config/`.
Restart it to pick up code changes.

In VS Code, the **Home Assistant** launch configuration (`.vscode/launch.json`)
runs the same under the debugger, so breakpoints in the integrations and the API
packages work.

The repository includes a devcontainer (`.devcontainer/`) that installs
everything with `scripts/setup`. Inside a container, Home Assistant cannot see
mDNS from your network, so add the Nymo by its IP address there. To test
discovery, run `scripts/develop` directly on your machine after the install
commands above.

## Publishing
### Publish the API package

The API package is published from `libraries/api` by manually running
`.github/workflows/publish-api.yml`. It uses PyPI Trusted Publishing.

To publish a version:

1. Update the `version` in `libraries/api/pyproject.toml`
2. Commit and push the change.
3. Open the repository's **Actions** tab and select **Publish API package**.
4. Click **Run workflow**, select the branch containing the version change,
   and run it.

Once it's published, don't forget to modify the version within the HomeAssistant integration manifest.

### Publish the local API package

The local API package (`solyx-energy-local-api-client`, used by Solyx Energy
Local) is published the same way from `libraries/local-api`, with
`.github/workflows/publish-local-api.yml` (**Publish local API package**). Its
version is in `libraries/local-api/pyproject.toml`; the integration requires it
in `custom_components/solyx_energy_local/manifest.json`.

### Publish to the `homeassistant/core` repository
When you're ready to submit to home-assistant/core, copy these folders to to the HomeAssistant fork within the organization.
- `custom_components/solyx_energy/`
- `tests/components/solyx_energy/`
