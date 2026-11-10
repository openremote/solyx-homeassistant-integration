# Home Assistant integration for Solyx Energy devices

Home Assistant integration for controlling and gaining insight in Solyx Energy devices

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
