# Home Assistant integration for Solyx Energy devices

Home Assistant integration for controlling and gaining insight in Solyx Energy devices

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```

This installs `homeassistant`, `pytest`, and `pytest-asyncio`.  
When you're ready to submit to home-assistant/core, copy:
- `homeassistant/components/solyx_energy/`
- `tests/components/solyx_energy/`

(Do *not* copy `tests/conftest.py` — HA Core has its own.)