from __future__ import annotations

import re
from pathlib import Path

from app.web import LEGACY_SETTING_KEYS, get_global_settings, handle_request

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "app" / "static" / "app.js"


def frontend_endpoints() -> set[str]:
    source = APP_JS.read_text(encoding="utf-8")
    return set(re.findall(r'["\'](/api/[^"\']+)["\']', source))


def test_smart_mud_home_page_loads_without_expected_api_404s():
    status, _headers, body = handle_request("/")

    assert status == 200
    assert b"Smart MUD" in body
    for endpoint in frontend_endpoints():
        endpoint_status, _endpoint_headers, _endpoint_body = handle_request(endpoint)
        assert endpoint_status != 404, endpoint


def test_frontend_settings_call_succeeds():
    status, headers, body = handle_request("/api/settings/global")

    assert status == 200
    assert headers["content-type"].startswith("application/json")
    assert b"Smart MUD" in body


def test_global_settings_are_smart_mud_specific():
    settings = get_global_settings()

    assert settings["app_name"] == "Smart MUD"
    assert settings["default_world_id"] == "shattered_realms"
    assert settings["runtime_mode"] == "smart_mud"
    assert "terminal_colors" in settings
    assert "smart_mud_settings" in settings


def test_global_settings_do_not_return_legacy_campaign_image_or_comfyui_settings():
    settings = get_global_settings()
    lowered_keys = {key.lower() for key in settings}

    assert lowered_keys.isdisjoint(LEGACY_SETTING_KEYS)


def test_no_old_campaign_runtime_settings_are_required_by_frontend():
    source = APP_JS.read_text(encoding="utf-8").lower()

    assert "campaign" not in source
    assert "comfy" not in source
    assert "image_generation" not in source
    assert frontend_endpoints() == {"/api/settings/global"}
