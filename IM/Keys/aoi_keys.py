"""WISVision IM AOI key bindings.

Runtime config:
    C:\\WISVision\\Config\\AOIKeys.ini

Key logs (same layout as clsLog.WriteLog):
    {root}/AOIKeys_LAST.txt
    {root}/{date}/AOIKeys_{date}.txt

Call shape:
    load()
    process_key(e.KeyData)      # int WinForms Keys or "F5" / "Ctrl+F5"
    try_get_action("NumPad3")   # no log
"""

from __future__ import annotations

import os
import threading
from datetime import datetime

MODULE_NAME = "AOIKeys"
DEFAULT_CONFIG_PATH = r"C:\WISVision\Config\AOIKeys.ini"
DEFAULT_LOG_ROOT = r"C:\WISVision\Log"
DATE_FORMAT = "%Y%m%d"
DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d", "%Y_%m_%d")

MOD_SHIFT = 0x00010000
MOD_CONTROL = 0x00020000
MOD_ALT = 0x00040000
KEY_CODE_MASK = 0x0000FFFF
MOD_MASK = MOD_SHIFT | MOD_CONTROL | MOD_ALT

AOI_ACTIONS = (
    "Start",
    "Stop",
    "Pause",
    "Auto",
    "Manual",
    "Grab",
    "Live",
    "Align",
    "OK",
    "NG",
    "Retry",
    "Skip",
    "Next",
    "Prev",
    "NextRow",
    "PrevRow",
    "Home",
    "Save",
    "Recipe",
    "Class1",
    "Class2",
    "Class3",
    "Class4",
    "Class5",
    "Class6",
    "Class7",
    "Class8",
    "Class9",
)

CLASS_ACTIONS = tuple(f"Class{n}" for n in range(1, 10))

DEFAULT_BINDINGS: dict[str, str] = {
    "Start": "F5",
    "Stop": "Escape",
    "Pause": "F6",
    "Auto": "F4",
    "Manual": "F3",
    "Grab": "F2",
    "Live": "F1",
    "Align": "A",
    "OK": "Enter",
    "NG": "Space",
    "Retry": "R",
    "Skip": "S",
    "Next": "Right",
    "Prev": "Left",
    "NextRow": "Down",
    "PrevRow": "Up",
    "Home": "Home",
    "Save": "F9",
    "Recipe": "F10",
    "Class1": "D1,NumPad1",
    "Class2": "D2,NumPad2",
    "Class3": "D3,NumPad3",
    "Class4": "D4,NumPad4",
    "Class5": "D5,NumPad5",
    "Class6": "D6,NumPad6",
    "Class7": "D7,NumPad7",
    "Class8": "D8,NumPad8",
    "Class9": "D9,NumPad9",
}

# WinForms Keys / virtual-key values.
KEY_CODES: dict[str, int] = {
    "BACK": 8,
    "BACKSPACE": 8,
    "TAB": 9,
    "ENTER": 13,
    "RETURN": 13,
    "SHIFTKEY": 16,
    "CONTROLKEY": 17,
    "ALTKEY": 18,
    "PAUSEKEY": 19,
    "CAPSLOCK": 20,
    "ESCAPE": 27,
    "ESC": 27,
    "SPACE": 32,
    "SPACEBAR": 32,
    "PAGEUP": 33,
    "PRIOR": 33,
    "PAGEDOWN": 34,
    "PAGEDN": 34,
    "END": 35,
    "HOME": 36,
    "LEFT": 37,
    "UP": 38,
    "RIGHT": 39,
    "DOWN": 40,
    "INSERT": 45,
    "INS": 45,
    "DELETE": 46,
    "DEL": 46,
    "MULTIPLY": 106,
    "ADD": 107,
    "SUBTRACT": 109,
    "DECIMAL": 110,
    "DIVIDE": 111,
    "NUMLOCK": 144,
    "SCROLL": 145,
}
for _i in range(10):
    KEY_CODES[f"D{_i}"] = 48 + _i
    KEY_CODES[str(_i)] = 48 + _i
    KEY_CODES[f"NUMPAD{_i}"] = 96 + _i
for _i, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    KEY_CODES[_ch] = 65 + _i
for _i in range(1, 25):
    KEY_CODES[f"F{_i}"] = 111 + _i

_CANONICAL_KEY = {
    8: "Backspace",
    9: "Tab",
    13: "Enter",
    27: "Escape",
    32: "Space",
    33: "PageUp",
    34: "PageDown",
    35: "End",
    36: "Home",
    37: "Left",
    38: "Up",
    39: "Right",
    40: "Down",
    45: "Insert",
    46: "Delete",
}
for _i in range(10):
    _CANONICAL_KEY[48 + _i] = f"D{_i}"
    _CANONICAL_KEY[96 + _i] = f"NumPad{_i}"
for _i, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _CANONICAL_KEY[65 + _i] = _ch
for _i in range(1, 25):
    _CANONICAL_KEY[111 + _i] = f"F{_i}"

_MOD_NAMES = (
    (MOD_CONTROL, "Ctrl", ("CTRL", "CONTROL")),
    (MOD_ALT, "Alt", ("ALT", "MENU")),
    (MOD_SHIFT, "Shift", ("SHIFT",)),
)

_lock = threading.Lock()
_log_root = DEFAULT_LOG_ROOT
_config_path = DEFAULT_CONFIG_PATH
_key_to_action: dict[int, str] = {}
_action_to_keys: dict[str, list[int]] = {}
_loaded = False


def set_config_path(path: str | os.PathLike[str]) -> None:
    global _config_path, _loaded
    _config_path = str(path)
    _loaded = False


def config_path() -> str:
    return _config_path


def set_log_root(path: str | os.PathLike[str]) -> None:
    global _log_root
    _log_root = str(path)


def log_root() -> str:
    return _log_root


def parse_key(text: str | int | None) -> int:
    if text is None:
        return 0
    if isinstance(text, int):
        return _normalize(text)
    raw = str(text).strip()
    if raw == "":
        return 0
    if raw.isdigit() and len(raw) > 2:
        return _normalize(int(raw))

    mods = 0
    parts = [p.strip() for p in raw.replace("-", "+").split("+") if p.strip()]
    if not parts:
        return 0
    key_part = parts[-1]
    for part in parts[:-1]:
        token = part.upper().replace(" ", "")
        matched = False
        for bit, _canon, aliases in _MOD_NAMES:
            if token in aliases:
                mods |= bit
                matched = True
                break
        if not matched:
            raise ValueError(f"unknown modifier: {part}")
    code = _lookup_key_token(key_part)
    if code == 0:
        raise ValueError(f"unknown key: {key_part}")
    return _normalize(mods | code)


def key_name(code: int | str | None) -> str:
    if code is None:
        return ""
    if isinstance(code, str):
        try:
            code = parse_key(code)
        except ValueError:
            return code.strip()
    code = _normalize(int(code))
    if code == 0:
        return ""
    mods = []
    for bit, canon, _aliases in _MOD_NAMES:
        if code & bit:
            mods.append(canon)
    base = _CANONICAL_KEY.get(code & KEY_CODE_MASK)
    if not base:
        base = f"0x{code & KEY_CODE_MASK:02X}"
    return "+".join(mods + [base])


def bind(action: str, keys: str | list[str] | int | None) -> None:
    action = (action or "").strip()
    if not action:
        raise ValueError("action is empty")
    codes = _parse_key_list(keys)
    with _lock:
        _bind_action(action, codes)


def bind_class(class_no: int, keys: str | list[str] | int | None) -> None:
    n = int(class_no)
    if n < 1 or n > 9:
        raise ValueError("class_no must be 1..9")
    bind(f"Class{n}", keys)


def class_no_from_action(action: str | None) -> int | None:
    if not action:
        return None
    text = str(action).strip()
    if len(text) < 6 or not text.lower().startswith("class"):
        return None
    rest = text[5:]
    if not rest.isdigit():
        return None
    n = int(rest)
    if n < 1 or n > 9:
        return None
    return n


def try_get_action(key: int | str | None) -> str | None:
    _ensure_loaded()
    try:
        code = parse_key(key) if not isinstance(key, int) else _normalize(key)
    except ValueError:
        return None
    if code == 0:
        return None
    with _lock:
        return _key_to_action.get(code)


def process_key(key: int | str | None, log: bool = True) -> str | None:
    action = try_get_action(key)
    if action and log:
        write_key_log(action, key_name(key))
    return action


def load(path: str | os.PathLike[str] | None = None) -> dict[str, str]:
    global _loaded
    ini_path = str(path) if path is not None else _config_path
    bindings = dict(DEFAULT_BINDINGS)
    if os.path.isfile(ini_path):
        bindings.update(_read_ini(ini_path))
    with _lock:
        _clear_maps()
        for action, keys in bindings.items():
            try:
                _bind_action(action, _parse_key_list(keys))
            except ValueError:
                continue
        _loaded = True
    return current_bindings()


def save_default(path: str | os.PathLike[str] | None = None) -> str:
    dest = str(path) if path is not None else _config_path
    folder = os.path.dirname(dest)
    if folder:
        os.makedirs(folder, exist_ok=True)
    data = _default_ini_bytes()
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    load(dest)
    return dest


def current_bindings() -> dict[str, str]:
    with _lock:
        out: dict[str, str] = {}
        for action, codes in _action_to_keys.items():
            out[action] = ",".join(key_name(code) for code in codes)
        return out


def last_path(name: str = MODULE_NAME) -> str:
    return os.path.join(_log_root, f"{name}_LAST.txt")


def daily_directory(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return os.path.join(_log_root, _date_stamp(now))


def daily_path(name: str = MODULE_NAME, now: datetime | None = None) -> str:
    now = now or datetime.now()
    date = _date_stamp(now)
    return os.path.join(daily_directory(now), f"{name}_{date}.txt")


def write_key_log(
    action: str | None,
    key: str | int | None = None,
    new_last: bool = False,
) -> None:
    msg = (action or "").strip()
    key_text = key_name(key) if key is not None and key != "" else ""
    if key_text:
        msg = f"Action={msg} Key={key_text}" if msg else f"Key={key_text}"
    elif msg:
        msg = f"Action={msg}"
    now = datetime.now()
    line = f"{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} : {msg}\n"
    with _lock:
        os.makedirs(_log_root, exist_ok=True)
        os.makedirs(daily_directory(now), exist_ok=True)
        _write_line_flush(last_path(), line, new_last)
        _write_line_flush(daily_path(now=now), line, False)


def reset_for_tests() -> None:
    global _loaded
    with _lock:
        _apply_defaults_unlocked()
        _loaded = True


def _ensure_loaded() -> None:
    if not _loaded:
        load()


def _apply_defaults_unlocked() -> None:
    _clear_maps()
    for action, keys in DEFAULT_BINDINGS.items():
        _bind_action(action, _parse_key_list(keys))


def _clear_maps() -> None:
    _key_to_action.clear()
    _action_to_keys.clear()


def _bind_action(action: str, codes: list[int]) -> None:
    old = _action_to_keys.get(action, [])
    for code in old:
        if _key_to_action.get(code) == action:
            del _key_to_action[code]
    unique: list[int] = []
    for code in codes:
        if code == 0:
            continue
        _key_to_action[code] = action
        if code not in unique:
            unique.append(code)
    if unique:
        _action_to_keys[action] = unique
    elif action in _action_to_keys:
        del _action_to_keys[action]


def _parse_key_list(keys: str | list[str] | int | None) -> list[int]:
    if keys is None:
        return []
    if isinstance(keys, int):
        code = _normalize(keys)
        return [code] if code else []
    if isinstance(keys, (list, tuple)):
        parts = list(keys)
    else:
        parts = [p.strip() for p in str(keys).split(",")]
    codes: list[int] = []
    for part in parts:
        if part is None or str(part).strip() == "":
            continue
        codes.append(parse_key(part))
    return codes


def _lookup_key_token(token: str) -> int:
    name = token.strip().upper().replace(" ", "")
    if name in KEY_CODES:
        return KEY_CODES[name]
    if name.startswith("VK_") and name[3:] in KEY_CODES:
        return KEY_CODES[name[3:]]
    if name.startswith("KEYS.") and name[5:] in KEY_CODES:
        return KEY_CODES[name[5:]]
    return 0


def _normalize(code: int) -> int:
    return (int(code) & KEY_CODE_MASK) | (int(code) & MOD_MASK)


def _date_stamp(now: datetime) -> str:
    for fmt in DATE_FORMATS:
        stamp = now.strftime(fmt)
        if os.path.isdir(os.path.join(_log_root, stamp)):
            return stamp
    return now.strftime(DATE_FORMAT)


def _write_line_flush(path: str, text: str, new_file: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT
    if new_file or not os.path.isfile(path):
        flags |= os.O_TRUNC
    else:
        flags |= os.O_APPEND
    fd = os.open(path, flags, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_ini(path: str) -> dict[str, str]:
    text = _read_text(path)
    out: dict[str, str] = {}
    in_section = True
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            in_section = name.lower() in ("", "aoikeys", "keys")
            continue
        if not in_section or "=" not in line:
            continue
        action, value = line.split("=", 1)
        action = action.strip()
        value = value.strip()
        if action:
            out[action] = value
    return out


def _read_text(path: str) -> str:
    with open(path, "rb") as handle:
        data = handle.read()
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp949", errors="replace")


def _default_ini_bytes() -> bytes:
    template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AOIKeys.ini")
    if os.path.isfile(template):
        with open(template, "rb") as handle:
            return handle.read()
    lines = [
        "; WISVision IM AOI Keys",
        "; 경로: C:\\WISVision\\Config\\AOIKeys.ini",
        "; 한 줄: 동작=키   (여러 키는 콤마)",
        "[AOIKeys]",
    ]
    for action in AOI_ACTIONS:
        lines.append(f"{action}={DEFAULT_BINDINGS[action]}")
    return ("\n".join(lines) + "\n").encode("utf-8")


reset_for_tests()
_loaded = True
