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


def add_back_only(
    options: Union[Dict[str, Any], Iterable[Dict[str, Any]], None], setter: Callable
) -> List[Dict[str, Any]]:
    """Return ``options`` with only a Back entry.

    Parameters
    ----------
    options
        Base option or list of options for the menu node.
    setter
        Callback to execute for the back selection. It will be called
        with ``raw_string`` set to ``"back"``.
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
    return opts


def add_back_next(
    options: Union[Dict[str, Any], Iterable[Dict[str, Any]], None], setter: Callable
) -> List[Dict[str, Any]]:
    """Return ``options`` with standard Back/Next entries."""

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
    opts.append({"desc": "Next", "goto": _run("skip")})
    return opts


def toggle_multi_select(choice: str, options: Iterable[str], selected: List[str]) -> bool:
    """Toggle ``choice`` in ``selected`` if valid.

    Parameters
    ----------
    choice
        Option label or numeric index (starting at 1).
    options
        Iterable of all valid option labels.
    selected
        List of currently selected options. Modified in place.

    Returns
    -------
    bool
        ``True`` if ``choice`` was recognized and toggled, ``False`` otherwise.
    """

    items = list(options)
    value = None
    c = str(choice).strip().lower()
    if c.isdigit():
        idx = int(c) - 1
        if 0 <= idx < len(items):
            value = items[idx]
    else:
        for opt in items:
            if opt.lower() == c:
                value = opt
                break
    if value is None:
        return False
    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)
    return True


def format_multi_select(options: Iterable[str], selected: Iterable[str]) -> str:
    """Return checkbox lines for ``options`` given ``selected``."""

    selected_set = set(selected)
    lines = []
    for idx, opt in enumerate(options, 1):
        mark = "X" if opt in selected_set else " "
        lines.append(f"{idx}. [{mark}] {opt}")
    return "\n".join(lines)
