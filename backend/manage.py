"""Project lifecycle management: status / stop / start for frontend + backend."""

import sys
import os
import subprocess
import socket
import time
import platform
from pathlib import Path

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
LOGS_DIR = PROJECT_ROOT / "logs"
IS_WIN = platform.system() == "Windows"

LOGS_DIR.mkdir(exist_ok=True)


# ── port helpers ────────────────────────────────────────

def _is_port_open(port: int) -> bool:
    """Check if any process is listening on the given TCP port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


def _pid_by_port(port: int) -> int | None:
    """Return PID of the process listening on `port`, or None."""
    if IS_WIN:
        try:
            out = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            ).stdout
            for line in out.splitlines():
                if "LISTENING" in line and f":{port}" in line:
                    return int(line.strip().split()[-1])
        except Exception:
            pass
    else:
        try:
            out = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            ).stdout
            pid = out.strip()
            if pid:
                return int(pid)
        except Exception:
            try:
                out = subprocess.run(
                    ["ss", "-tlpn"], capture_output=True, text=True, timeout=5
                ).stdout
                for line in out.splitlines():
                    if f":{port}" in line and "pid=" in line:
                        import re
                        m = re.search(r"pid=(\d+)", line)
                        if m:
                            return int(m.group(1))
            except Exception:
                pass
    return None


def _kill_by_port(port: int) -> bool:
    """Kill whatever is listening on `port`. Returns True if successful."""
    pid = _pid_by_port(port)
    if not pid:
        return True  # nothing to kill

    if IS_WIN:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass

    time.sleep(1)
    return not _is_port_open(port)


# ── commands ────────────────────────────────────────────

def cmd_status():
    be = _is_port_open(BACKEND_PORT)
    fe = _is_port_open(FRONTEND_PORT)
    be_pid = _pid_by_port(BACKEND_PORT)
    fe_pid = _pid_by_port(FRONTEND_PORT)

    def label(ok, port, pid):
        if ok:
            return f"✅ 运行中  端口:{port}  PID:{pid or '?'}"
        else:
            return f"❌ 未运行  端口:{port}"

    print("=" * 45)
    print(f"  后端 (FastAPI)   {label(be, BACKEND_PORT, be_pid)}")
    print(f"  前端 (Vite)      {label(fe, FRONTEND_PORT, fe_pid)}")
    print("=" * 45)


def cmd_stop():
    print("正在停止所有服务...\n")

    be_ok = _is_port_open(BACKEND_PORT)
    fe_ok = _is_port_open(FRONTEND_PORT)

    if not be_ok and not fe_ok:
        print("❌ 前端和后端均未运行")
        return

    for name, port, was_running in [
        ("后端 (FastAPI)", BACKEND_PORT, be_ok),
        ("前端 (Vite)", FRONTEND_PORT, fe_ok),
    ]:
        if not was_running:
            print(f"  {name}: 未运行，跳过")
            continue
        pid = _pid_by_port(port)
        print(f"  {name}: 停止 PID={pid} ...", end=" ")
        if _kill_by_port(port):
            print("✅")
        else:
            print(f"⚠ 失败，手动杀: taskkill /PID {pid} /F" if IS_WIN else f"⚠ 失败，手动: kill -9 {pid}")

    print("\n完成")


def cmd_start():
    be_ok = _is_port_open(BACKEND_PORT)
    fe_ok = _is_port_open(FRONTEND_PORT)

    if be_ok and fe_ok:
        print("⚠ 前端和后端均在运行，无需重复启动")
        return

    # ── Backend ──
    if not be_ok:
        print("启动后端 ...")
        be_log = open(LOGS_DIR / "backend.log", "w")
        kwargs = dict(
            cwd=str(BACKEND_DIR),
            stdout=be_log, stderr=be_log,
            start_new_session=True,
        )
        if IS_WIN:
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        subprocess.Popen([sys.executable, str(BACKEND_DIR / "run.py")], **kwargs)
        time.sleep(3)
        if _is_port_open(BACKEND_PORT):
            print(f"  后端 ✅  http://localhost:{BACKEND_PORT}  (日志: logs/backend.log)")
        else:
            print("  后端 ⚠ 未响应，查看 logs/backend.log")
    else:
        print(f"后端已在运行 (端口 {BACKEND_PORT})，跳过")

    # ── Frontend ──
    if not fe_ok:
        print("启动前端 ...")
        fe_log = open(LOGS_DIR / "frontend.log", "w")
        npm_cmd = "npm.cmd" if IS_WIN else "npm"
        kwargs = dict(
            cwd=str(FRONTEND_DIR),
            stdout=fe_log, stderr=fe_log,
            start_new_session=True,
        )
        if IS_WIN:
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        subprocess.Popen([npm_cmd, "run", "dev"], **kwargs)
        time.sleep(4)
        if _is_port_open(FRONTEND_PORT):
            print(f"  前端 ✅  http://localhost:{FRONTEND_PORT}  (日志: logs/frontend.log)")
        else:
            print("  前端 ⚠ 未响应，查看 logs/frontend.log")
    else:
        print(f"前端已在运行 (端口 {FRONTEND_PORT})，跳过")

    print("\n启动完成")


# ── main ────────────────────────────────────────────────

if __name__ == "__main__":
    usage = """Usage:
  python manage.py status   查看前端 + 后端运行状态
  python manage.py stop     停止前端 + 后端
  python manage.py start    启动前端 + 后端"""
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "status":
        cmd_status()
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "start":
        cmd_start()
    else:
        print(f"未知命令: {cmd}")
        print(usage)
        sys.exit(1)
