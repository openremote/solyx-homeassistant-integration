# Home Assistant integration for Solyx Energy devices

Home Assistant integration for controlling and gaining insight in Solyx Energy devices

## Supported platforms

| Platform | Entities | Description |
|----------|----------|-------------|
| `sensor` | Power boiler, Energy to boiler, Grid power | Read-only measurements reported by the Nymo device |
| `select` | Operating mode | Switch between `DIRECT` and `MUTED` operating modes |
| `number` | Control value | Set the boiler control value (0–100%) |

## Install through Home Assistant
The integration has not been released to the official Home Assistant store yet.<br />
As an alternative, you can [install through HACS](#install-through-hacs)

## Install through HACS
You can install the **Solyx Energy** integration through HACS, the Home Assistant Community Store.<br />
This is meant for testing; so you will install an unstable version of the software.<br />
For stable versions, please read the [Install through Home Assistant](#install-through-home-assistant) guide

Requirements:
- A GitHub account (required for installing HACS)
- You have installed HACS through the guide on their [website](https://www.hacs.xyz/docs/use/download/download/).

Installation steps:
1. In the Home Assistant left sidebar, click on the HACS icon.
2. Click on the three dots on the top-right of your screen. → Select **Custom repositories**
3. In the repository field, fill in `https://github.com/openremote/solyx-homeassistant-integration`
4. In the type dropdown, select **Integration**.
5. Click on **Add**. After a couple of seconds, the text "Solyx Energy" with the URL will appear. You can now close this window.
6. In the search field, type in "Solyx Energy", click on it, and download the integration.
7. Restart Home Assistant
8. Once restarted, go to Settings → Devices & services → Click on **Add integration** on the bottom left → add the Solyx Energy integration.
9. Copy the Client ID, Client Secret and Nymo device ID from the Solyx Energy app, and paste them in here.
10. Press **Submit**, and you're good to go!

## Development

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ./libraries/api
python -m pytest
```

The first command installs `homeassistant`, pytest utilities, `ruff`, and
`mypy`. The second installs the local API package in editable mode.

Lint and type-check before submitting:

```bash
ruff check .
mypy libraries/api/solyx_energy_api custom_components
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

### Publish to the `homeassistant/core` repository
When you're ready to submit to home-assistant/core, copy these folders to to the HomeAssistant fork within the organization.
- `custom_components/solyx_energy/`
- `tests/components/solyx_energy/`

> **PLEASE DO NOT COPY `tests/components/solyx_energy/conftest.py`**, HomeAssistant has their own.
