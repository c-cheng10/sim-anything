"""Human-readable error messages for the CLI and the loop.

Pydantic's default ``ValidationError`` text uses dotted locations
(``joints.2.efort_limit``), repeats internal error types and links to
pydantic.dev. :func:`describe_exception` turns it into one line per error in
the repo's field-path style (``joints[2].efort_limit``, the same paths used in
``sources``/``estimates`` and in check fix hints) and suggests close field
names for unknown keys.
"""

from __future__ import annotations

import difflib
import types
import typing
from typing import Any, Iterable, Optional, Union

from pydantic import BaseModel, ValidationError

__all__ = ["describe_exception", "format_validation_error", "loc_to_path"]

_MAX_INPUT_REPR = 40


def _unwrap(ann: Any) -> list[Any]:
    """Flatten Optional/Union/Annotated into their member annotations."""
    origin = typing.get_origin(ann)
    if origin is Union or origin is types.UnionType:
        out: list[Any] = []
        for a in typing.get_args(ann):
            if a is not type(None):
                out += _unwrap(a)
        return out
    if origin is typing.Annotated:
        return _unwrap(typing.get_args(ann)[0])
    return [ann]


def _is_model(ann: Any) -> bool:
    return isinstance(ann, type) and issubclass(ann, BaseModel)


def _field(model: type[BaseModel], name: str) -> Optional[Any]:
    for fname, f in model.model_fields.items():
        if name == fname or name == f.alias:
            return f.annotation
    return None


def _walk(root: Optional[type[BaseModel]], loc: Iterable[Any]) -> tuple[str, list[Any]]:
    """Render ``loc`` as a bracket path and return the annotations it ends on.

    The annotations are empty when the walk lost track of the schema (then the
    path is rendered heuristically).
    """
    path = ""
    anns: list[Any] = [root] if root is not None else []
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
            nxt = []
            for a in anns:
                for u in _unwrap(a):
                    origin, args = typing.get_origin(u), typing.get_args(u)
                    if origin in (list, set, frozenset) and args:
                        nxt.append(args[0])
                    elif origin is tuple and args:
                        nxt.append(args[0] if (len(args) == 2 and args[1] is Ellipsis) or part >= len(args)
                                   else args[part])
            anns = nxt
            continue
        part = str(part)
        members = [u for a in anns for u in _unwrap(a)]
        # a union member tag (pydantic adds the member's name to the location)
        tagged = [m for m in members if _is_model(m) and m.__name__ == part]
        if tagged:
            anns = tagged
            continue
        nxt = [f for u in members if _is_model(u) for f in [_field(u, part)] if f is not None]
        if nxt:
            path += ("." if path else "") + part
            anns = nxt
            continue
        dicts = [u for u in members if typing.get_origin(u) is dict]
        if dicts:  # a key of a mapping such as `sources`
            path += f"[{part!r}]"
            anns = [typing.get_args(d)[1] for d in dicts if len(typing.get_args(d)) == 2]
            continue
        # unknown part: keep field-like names, drop pydantic's internal tags
        if not any(c in part for c in "[](), -") and not part[:1].isupper():
            path += ("." if path else "") + part
        anns = []
    return path, anns


def loc_to_path(loc: Iterable[Any], root: Optional[type[BaseModel]] = None) -> str:
    """``("joints", 2, "dh", "a")`` -> ``"joints[2].dh.a"``."""
    return _walk(root, loc)[0]


def _allowed_fields(anns: list[Any]) -> list[str]:
    names: list[str] = []
    for a in anns:
        for u in _unwrap(a):
            if _is_model(u):
                for fname, f in u.model_fields.items():
                    names.append(f.alias or fname)
    return sorted(set(names))


def _short(value: Any) -> Optional[str]:
    if isinstance(value, (dict, list, tuple)) or value is None:
        return None
    r = repr(value)
    return r if len(r) <= _MAX_INPUT_REPR else r[:_MAX_INPUT_REPR - 3] + "..."


def _message(err: dict[str, Any], root: Optional[type[BaseModel]]) -> tuple[str, str]:
    loc = tuple(err.get("loc", ()))
    kind = err.get("type", "")
    msg = str(err.get("msg", "invalid value"))
    for prefix in ("Value error, ", "Assertion failed, "):
        if msg.startswith(prefix):
            msg = msg[len(prefix):]
    if kind == "extra_forbidden" and loc:
        parent_path, parent = _walk(root, loc[:-1])
        key = str(loc[-1])
        path = f"{parent_path}.{key}" if parent_path else key
        allowed = _allowed_fields(parent)
        text = "unknown field"
        close = difflib.get_close_matches(key, allowed, n=3, cutoff=0.6)
        if close:
            text += "; did you mean " + " or ".join(f"'{c}'" for c in close) + "?"
        elif allowed:
            text += f" (allowed here: {', '.join(allowed)})"
        return path, text
    path, _ = _walk(root, loc)
    if kind == "missing":
        return path, "required field is missing"
    shown = _short(err.get("input"))
    if shown is not None and kind not in ("value_error", "assertion_error"):
        msg += f" (got {shown})"
    return path, msg


def format_validation_error(exc: ValidationError, root: Optional[type[BaseModel]] = None) -> list[str]:
    """One ``"<path>: <message>"`` line per error, without pydantic.dev URLs."""
    lines: list[str] = []
    for err in exc.errors(include_url=False):
        path, msg = _message(err, root)
        line = f"{path or '(top level)'}: {msg}"
        if line not in lines:
            lines.append(line)
    return lines


def _root_for(exc: ValidationError) -> Optional[type[BaseModel]]:
    title = getattr(exc, "title", None)
    if title == "Spec":
        from .spec import Spec

        return Spec
    if title == "Mapping":
        from .schemas import Mapping

        return Mapping
    return None


def describe_exception(exc: BaseException, what: str = "spec") -> str:
    """A friendly, possibly multi-line description of ``exc``.

    Schema errors become ``invalid <what>: N schema error(s)`` followed by one
    indented ``- path: message`` line per error; anything else is
    ``Type: message``.
    """
    if isinstance(exc, ValidationError):
        lines = format_validation_error(exc, _root_for(exc))
        head = f"invalid {what}: {len(lines)} schema error{'s' if len(lines) != 1 else ''}"
        return "\n".join([head] + [f"  - {ln}" for ln in lines])
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__
