"""Typed project configuration.

`project.yaml` and the web UI both hand this module raw, weakly-typed data:

- `project.yaml` is loaded with `yaml.safe_load`, so a hand-edited file can
  give any key any type (`rows: '3'` and `rows: 3` are both possible).
- The web UI POSTs a mix of plain `<input>` values (always strings via
  `e.target.value`) and slider values (real numbers) for the very same
  numeric fields, depending on how the user last touched the control.

`Config` is the single point where this gets coerced to real
int/float/bool/str values, once. Build it via `Config.from_dict(...)` -
never construct/mutate it from a raw dict directly - and treat instances as
read-only afterwards; every other module can then rely on the declared
types without re-casting at each read site.
"""

from dataclasses import dataclass, field, fields, asdict
from typing import Any, Callable, Dict, List, Optional


def coerce_bool(value: Any) -> bool:
    """The one true bool coercion rule for this project.

    Plain `bool('false')` is `True` in Python, which would silently invert
    `highlightChanges`/`crop` the moment either came back from YAML or the
    web UI as a string. Rule: the strings 'false', 'False', '0' and '' are
    False; every other string is True; non-string values fall back to
    Python's own `bool(...)`.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ('false', '0', '')
    if value is None:
        return False
    return bool(value)


def coerce_int(value: Any, default: int = 0) -> int:
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_str(value: Any, default: str = '') -> str:
    if value is None:
        return default
    return str(value)


def coerce_text_replacements(value: Any) -> List[Dict[str, str]]:
    """Keep only well-shaped `{old, new}` entries; drop anything else rather
    than raising, so a hand-edited list doesn't take down loading."""
    if not isinstance(value, list):
        return []
    result: List[Dict[str, str]] = []
    for item in value:
        if isinstance(item, dict) and 'old' in item and 'new' in item:
            result.append({'old': str(item['old']), 'new': str(item['new'])})
    return result


@dataclass
class Config:
    mainTexFile: str = ''

    rows: int = 3
    columns: int = 6
    blur: float = 1.0
    highlightChanges: bool = True

    # -1/absent: default thread pool size; 1: single-threaded; N>1: N workers.
    # Wired to compiler.setThreads() in compileProject.
    workers: int = -1

    startCommit: str = ''
    endCommit: str = ''

    crop: bool = False
    cropTwoPage: bool = False
    cropLeft: int = 0
    cropRight: int = 0
    cropTop: int = 0
    cropBottom: int = 0
    cropAltLeft: int = 0
    cropAltRight: int = 0
    cropAltTop: int = 0
    cropAltBottom: int = 0

    # How many commits to concatenate into one snapshot. 0 (or negative)
    # means no concatenation.
    concatCommits: int = 0

    # When a snapshot fails to compile, abort the run before encoding rather
    # than silently encoding a video with that commit's frame missing (ffmpeg
    # globs frames/*.png, so a gap shifts the whole timelapse). Set True to
    # deliberately render whatever frames succeeded - real LaTeX histories do
    # contain commits that legitimately do not compile.
    allowPartialRender: bool = False

    # TODO: maybe change to latexMode: pdflatex | luaLaTeX | xelatex...?
    latexCmd: str = 'latexmk -pdf -interaction=nonstopmode -synctex=1 -f'

    text_replacements: List[Dict[str, str]] = field(default_factory=list)

    overleafProjectId: str = ''
    overleafAuthToken: str = ''

    # Video settings
    framerate: int = 8
    videoscale: float = 0.25

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]], defaults: Optional[Dict[str, Any]] = None) -> 'Config':
        """Build a Config, coercing every recognised field exactly once.

        A field missing from `data` falls back to `defaults` (normally the
        parsed contents of default_config.yaml), and then to this
        dataclass's own field default if `defaults` doesn't have it
        either. Keys present in `data`/`defaults` that aren't a Config
        field are silently ignored, so a hand-edited project.yaml with
        stray or legacy keys (e.g. `startDate`) still loads without
        crashing - it just won't survive a subsequent serialize().
        """
        data = data or {}
        defaults = defaults or {}

        kwargs: Dict[str, Any] = {}
        for f in fields(cls):
            if f.name.startswith('_'):
                continue
            if f.name in data:
                raw = data[f.name]
            elif f.name in defaults:
                raw = defaults[f.name]
            else:
                continue  # keep this dataclass field's own default
            coercer = _FIELD_COERCERS.get(f.name, coerce_str)
            kwargs[f.name] = coercer(raw)
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Plain, YAML/JSON-safe dict - never dump the dataclass itself."""
        return {k: v for k, v in asdict(self).items() if not k.startswith('_')}


_FIELD_COERCERS: Dict[str, Callable[[Any], Any]] = {
    'rows': coerce_int,
    'columns': coerce_int,
    'blur': coerce_float,
    'highlightChanges': coerce_bool,
    'workers': coerce_int,
    'crop': coerce_bool,
    'cropTwoPage': coerce_bool,
    'cropLeft': coerce_int,
    'cropRight': coerce_int,
    'cropTop': coerce_int,
    'cropBottom': coerce_int,
    'cropAltLeft': coerce_int,
    'cropAltRight': coerce_int,
    'cropAltTop': coerce_int,
    'cropAltBottom': coerce_int,
    'concatCommits': coerce_int,
    'allowPartialRender': coerce_bool,
    'text_replacements': coerce_text_replacements,
    'framerate': coerce_int,
    'videoscale': coerce_float,
}
