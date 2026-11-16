"""Shot2Key launcher: verify prerequisites, install what is missing, run both servers.

Usage (normally via ``start.bat``):

    backend\\.venv\\Scripts\\python.exe launcher.py

Steps
-----
1. Check the agent CLIs (``agy`` / ``codex``). Missing ones stop the launch with
   the current install command and the official docs URL.
2. Create ``backend/.venv`` and install ``backend/requirements.txt`` when needed.
3. Run ``npm install`` in ``frontend/`` when ``node_modules`` is missing.
4. Put the ffmpeg shipped by ``imageio-ffmpeg`` on the backend's PATH.
5. Start backend + frontend, stream prefixed logs, open the browser.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_DIR = BACKEND_DIR / ".venv"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
REQUIREMENTS_STAMP = VENV_DIR / ".requirements.installed"
NPM_STAMP = FRONTEND_DIR / "node_modules" / ".package.installed"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

#: Which CLIs must exist before the app is useful. Override with
#: SHOT2KEY_REQUIRE_CLI="agy" (or "" to skip the check entirely).
REQUIRED_CLIS = ("agy", "codex")

CLI_HELP = {
    "agy": (
        "Antigravity CLI (agy)",
        "irm https://antigravity.google/cli/install.ps1 | iex",
        "https://antigravity.google/docs/cli/reference",
    ),
    "codex": (
        "OpenAI Codex CLI (codex)",
        "npm install -g @openai/codex@latest",
        "https://github.com/openai/codex",
    ),
}

_PRINT_LOCK = threading.Lock()


def _log(prefix: str, line: str) -> None:
    with _PRINT_LOCK:
        print(f"[{prefix}] {line}", flush=True)


def _banner(text: str) -> None:
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


# --------------------------------------------------------------------------
# Prerequisite checks
# --------------------------------------------------------------------------
def _which(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = {
            "agy": [local / "agy" / "bin" / "agy.exe"],
            "codex": [local / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe"],
        }.get(name, [])
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def required_clis() -> tuple[str, ...]:
    override = os.environ.get("SHOT2KEY_REQUIRE_CLI")
    if override is None:
        return REQUIRED_CLIS
    return tuple(item.strip() for item in override.split(",") if item.strip())


def check_clis() -> list[str]:
    """Return the required CLIs that are not installed."""
    return [name for name in required_clis() if _which(name) is None]


def print_cli_help(missing: list[str]) -> None:
    print()
    print("[ERROR] CLI wajib belum terpasang: " + ", ".join(missing))
    print()
    for name in missing:
        title, command, url = CLI_HELP[name]
        print(f"  {title}")
        print(f"    Windows PowerShell : {command}")
        print(f"    Docs / repo        : {url}")
        print()
    print("  Setelah terpasang, tutup dan buka lagi terminal ini (PATH perlu di-refresh),")
    print("  lalu jalankan start.bat kembali.")
    print()
    print("  Ingin melewati pengecekan ini? set SHOT2KEY_REQUIRE_CLI=agy (atau kosong).")
    print()


def find_base_python() -> list[str] | None:
    """Interpreter used to create the venv (3.12/3.11 preferred for wheels)."""
    if os.name == "nt":
        for version in ("-3.12", "-3.11", "-3.10", "-3"):
            try:
                probe = subprocess.run(
                    ["py", version, "-c", "import sys;print(sys.version_info[:2])"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if probe.returncode == 0:
                return ["py", version]
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return [found]
    return None


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_venv() -> Path:
    python = venv_python()
    if not python.is_file():
        base = find_base_python()
        if base is None:
            raise SystemExit(
                "[ERROR] Python 3.10+ tidak ditemukan. Install dari https://www.python.org/downloads/"
            )
        _log("SYS", "Membuat virtual environment backend/.venv ...")
        result = subprocess.run([*base, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0 or not python.is_file():
            raise SystemExit("[ERROR] Gagal membuat virtual environment.")
    return python


def requirements_changed() -> bool:
    if not REQUIREMENTS_STAMP.is_file():
        return True
    return REQUIREMENTS.stat().st_mtime > REQUIREMENTS_STAMP.stat().st_mtime


def ensure_backend_deps(python: Path) -> None:
    if not requirements_changed():
        _log("SYS", "Dependensi backend sudah siap.")
        return
    _log("SYS", "Menginstall dependensi backend (requirements.txt) ...")
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip", "-q"], check=False)
    result = subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    )
    if result.returncode != 0:
        raise SystemExit("[ERROR] Gagal menginstall dependensi backend.")
    shutil.copyfile(REQUIREMENTS, REQUIREMENTS_STAMP)


def ensure_frontend_deps() -> None:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm is None:
        raise SystemExit(
            "[ERROR] Node.js / npm tidak ditemukan. Install Node.js 18+ dari https://nodejs.org/"
        )
    package_json = FRONTEND_DIR / "package.json"
    needs_install = (
        not (FRONTEND_DIR / "node_modules").is_dir()
        or not NPM_STAMP.is_file()
        or package_json.stat().st_mtime > NPM_STAMP.stat().st_mtime
    )
    if not needs_install:
        _log("SYS", "Dependensi frontend sudah siap.")
        return
    _log("SYS", "Menginstall dependensi frontend (npm install) ...")
    result = subprocess.run([npm, "install"], cwd=str(FRONTEND_DIR))
    if result.returncode != 0:
        raise SystemExit("[ERROR] Gagal menginstall dependensi frontend.")
    shutil.copyfile(package_json, NPM_STAMP)


def ffmpeg_from_venv(python: Path) -> str | None:
    """Ask the venv for the ffmpeg binary imageio-ffmpeg ships."""
    try:
        probe = subprocess.run(
            [str(python), "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    path = probe.stdout.strip()
    return path if probe.returncode == 0 and path and Path(path).is_file() else None


# --------------------------------------------------------------------------
# Process management
# --------------------------------------------------------------------------
def _stream_output(proc: subprocess.Popen[str], prefix: str) -> None:
    assert proc.stdout is not None
    try:
        for raw_line in iter(proc.stdout.readline, ""):
            line = raw_line.rstrip("\r\n")
            if line:
                _log(prefix, line)
    except Exception:
        pass


def _kill_tree(proc: subprocess.Popen[str] | None, name: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    _log("SYS", f"Menghentikan {name} (PID {proc.pid})...")
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _wait_and_open_browser(url: str, stop_event: threading.Event) -> None:
    deadline = time.monotonic() + 40.0
    while time.monotonic() < deadline and not stop_event.is_set():
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/api/health", timeout=1):
                break
        except Exception:
            time.sleep(0.5)
    if stop_event.is_set():
        return
    time.sleep(1.5)
    _log("SYS", f"Membuka browser: {url}")
    webbrowser.open(url)


def main() -> int:
    _banner("Shot2Key - Setup & Launcher")

    missing = check_clis()
    if missing:
        print_cli_help(missing)
        return 1

    python = ensure_venv()
    ensure_backend_deps(python)
    ensure_frontend_deps()

    ffmpeg = ffmpeg_from_venv(python)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["FORCE_COLOR"] = "0"
    env["NO_COLOR"] = "1"
    if ffmpeg:
        env["SHOT2KEY_FFMPEG"] = ffmpeg
        env["PATH"] = str(Path(ffmpeg).parent) + os.pathsep + env.get("PATH", "")
        _log("SYS", f"ffmpeg: {ffmpeg}")
    else:
        _log("SYS", "ffmpeg dari imageio-ffmpeg tidak ditemukan; memakai ffmpeg sistem bila ada.")

    uvicorn = VENV_DIR / ("Scripts/uvicorn.exe" if os.name == "nt" else "bin/uvicorn")
    be_cmd = (
        [str(uvicorn), "main:app", "--port", str(BACKEND_PORT)]
        if uvicorn.is_file()
        else [str(python), "-m", "uvicorn", "main:app", "--port", str(BACKEND_PORT)]
    )
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    fe_cmd = [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT)]

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

    _log("SYS", f"Menjalankan Backend (port {BACKEND_PORT}) dan Frontend (port {FRONTEND_PORT})...")
    _log("SYS", "Tekan Ctrl+C atau tutup window ini untuk menghentikan keduanya.")

    be_proc = subprocess.Popen(
        be_cmd,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=creationflags,
    )
    fe_proc = subprocess.Popen(
        fe_cmd,
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=creationflags,
    )

    stop_event = threading.Event()

    def _handle_signal(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handle_signal)

    for target, args in (
        (_stream_output, (be_proc, "BE")),
        (_stream_output, (fe_proc, "FE")),
        (_wait_and_open_browser, (FRONTEND_URL, stop_event)),
    ):
        threading.Thread(target=target, args=args, daemon=True).start()

    try:
        while not stop_event.is_set():
            be_code = be_proc.poll()
            fe_code = fe_proc.poll()
            if be_code is not None:
                _log("SYS", f"Backend berhenti dengan kode {be_code}.")
                break
            if fe_code is not None:
                _log("SYS", f"Frontend berhenti dengan kode {fe_code}.")
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        _kill_tree(fe_proc, "Frontend")
        _kill_tree(be_proc, "Backend")
        _log("SYS", "Semua server telah dihentikan.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
