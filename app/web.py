"""Minimal Smart MUD web endpoints.

The desktop shell loads this module for the Phase 1 browser UI.  Keep the API
surface intentionally small and MUD-specific; do not expose legacy Adventure
Guild AI, campaign, image generation, or ComfyUI settings here.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Callable
from urllib.parse import parse_qs

SMART_MUD_SETTINGS: dict[str, Any] = {
    "app_name": "Smart MUD",
    "theme": "dark",
    "terminal_colors": {
        "background": "#05070a",
        "foreground": "#d7e1ff",
        "accent": "#7dd3fc",
        "error": "#f87171",
    },
    "developer_tools_enabled": False,
    "default_world_id": "shattered_realms",
    "runtime_mode": "smart_mud",
    "smart_mud_settings": {
        "terminal_prompt": ">",
        "startup_view": "terminal",
    },
}

LEGACY_SETTING_KEYS = frozenset(
    {
        "campaign",
        "campaign_settings",
        "campaign_runtime",
        "image",
        "image_settings",
        "image_generation",
        "comfyui",
        "comfyui_settings",
        "adventure_guild_ai",
        "ai_settings",
    }
)


def get_global_settings() -> dict[str, Any]:
    """Return compatibility settings for the Smart MUD frontend."""
    return json.loads(json.dumps(SMART_MUD_SETTINGS))


def _json_response(payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    return int(status), {"content-type": "application/json; charset=utf-8"}, body


def handle_request(path: str, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
    """Handle the small Smart MUD HTTP API used during initial page load."""
    normalized_method = method.upper()
    if normalized_method != "GET":
        return _json_response({"error": "method not allowed"}, HTTPStatus.METHOD_NOT_ALLOWED)
    if path == "/api/settings/global":
        return _json_response(get_global_settings())
    if path in {"/", "/index.html"}:
        return (
            int(HTTPStatus.OK),
            {"content-type": "text/html; charset=utf-8"},
            b'<!doctype html><div id="app">Smart MUD</div><script src="/static/app.js"></script>',
        )
    return _json_response({"error": "not found"}, HTTPStatus.NOT_FOUND)


def application(environ: dict[str, Any], start_response: Callable[[str, list[tuple[str, str]]], None]) -> list[bytes]:
    """WSGI adapter for the desktop runtime."""
    path = environ.get("PATH_INFO", "/")
    if environ.get("QUERY_STRING"):
        parse_qs(environ["QUERY_STRING"])
    status_code, headers, body = handle_request(path, environ.get("REQUEST_METHOD", "GET"))
    reason = HTTPStatus(status_code).phrase
    start_response(f"{status_code} {reason}", list(headers.items()))
    return [body]
