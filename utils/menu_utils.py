"""Helpers for building EvMenu nodes."""

from typing import Any, Callable, Iterable, List, Dict, Union


def add_back_skip(options: Union[Dict[str, Any], Iterable[Dict[str, Any]], None], setter: Callable) -> List[Dict[str, Any]]:
    """Return ``options`` with standard Back/Skip entries.

    Parameters
    ----------
    options
        Base option or list of options for the menu node.
    setter
        Callback to execute for back/skip selections. It will be called
        with ``raw_string`` set to ``"back"`` or ``"skip"`` respectively.
    """
    opts: List[Dict[str, Any]]
    if options is None:
        opts = []
    elif isinstance(options, dict):
        opts = [options]
    else:
        opts = list(options)

    def _run(value: str):
        def _inner(caller, raw_string=None, **kwargs):
            return setter(caller, value, **kwargs)
        return _inner

    opts.append({"desc": "Back", "goto": _run("back")})
    opts.append({"desc": "Skip", "goto": _run("skip")})
    return opts
