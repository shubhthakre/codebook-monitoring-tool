import sys
from pathlib import Path

# backend/  (this file lives in backend/app/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent

_LINUX_SYSTEM_CANDIDATES = (
    Path("/opt/oracle/instantclient_23_26"),
    Path("/opt/oracle/instantclient"),
)


def current_oracle_platform() -> str:
    return "windows" if sys.platform.startswith("win") else "linux"


def _dir_names(path: Path) -> list[str]:
    try:
        return [p.name.lower() for p in path.iterdir()]
    except OSError:
        return []


def _matches_current_os(path: Path) -> bool:
    """True only if this folder is Instant Client for the OS we are running on."""
    if not path.is_dir():
        return False
    names = _dir_names(path)
    has_windows = "oci.dll" in names
    has_linux = any(name.startswith("libclntsh") for name in names)
    if current_oracle_platform() == "windows":
        return has_windows
    return has_linux


def _candidate_dirs() -> list[Path]:
    platform = current_oracle_platform()
    candidates: list[Path] = [
        _BACKEND_ROOT / "instantclient" / platform,
        _BACKEND_ROOT / "instantclient",
    ]
    if platform == "windows":
        patterns = (
            "instantclient-basic-windows*/instantclient_*",
            "instantclient-basic-windows*",
            "instantclient-*/instantclient_*",
            "instantclient_*",
        )
    else:
        patterns = (
            "instantclient-basic-linux*/instantclient_*",
            "instantclient-basic-linux*",
            "instantclient_*",
            "instantclient-*/instantclient_*",
        )
    for pattern in patterns:
        candidates.extend(sorted(_BACKEND_ROOT.glob(pattern)))
    if platform == "linux":
        candidates.extend(_LINUX_SYSTEM_CANDIDATES)
    return candidates


def discover_oracle_client_dir() -> Path | None:
    """Find Instant Client in the project that matches Windows or Linux."""
    seen: set[Path] = set()
    for raw in _candidate_dirs():
        try:
            path = raw.resolve()
        except OSError:
            continue
        if path in seen:
            continue
        seen.add(path)
        if _matches_current_os(path):
            return path
    return None


def resolve_oracle_client_lib_dir(configured: str = "") -> str:
    """Use an explicit path if it matches this OS; otherwise auto-detect."""
    configured = (configured or "").strip()
    if configured:
        path = Path(configured).expanduser()
        if _matches_current_os(path):
            return str(path.resolve())
    found = discover_oracle_client_dir()
    if found is not None:
        return str(found)
    return configured
