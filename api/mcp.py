import asyncio
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.logger import logger

router = APIRouter()

PID_FILE = Path("mcp_server/mcp.pid")
LOG_FILE = Path("mcp_server/mcp_server.log")
SERVER_SCRIPT = "mcp_server/server/mcp_server.py"


class McpStatusResponse(BaseModel):
    running: bool
    pid: int | None = None
    uptime_seconds: int | None = None


def read_pid() -> int | None:
    try:
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            return pid
    except Exception:
        return None
    return None


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@router.get("/mcp/status", response_model=McpStatusResponse)
async def get_mcp_status():
    pid = read_pid()
    if not pid or not is_running(pid):
        return McpStatusResponse(running=False, pid=None, uptime_seconds=None)

    # get uptime (seconds) from /proc if available, otherwise approximate
    try:
        start_ts = os.stat(f"/proc/{pid}").st_ctime
        uptime = int(time.time() - start_ts)
    except Exception:
        uptime = None

    return McpStatusResponse(running=True, pid=pid, uptime_seconds=uptime)


@router.post("/mcp/start")
async def start_mcp_server():
    # Check if already running
    pid = read_pid()
    if pid and is_running(pid):
        return {"message": "MCP server already running", "pid": pid}

    # Ensure log dir
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Start subprocess and write pid
    try:
        # Spawn background shell to run server script
        cmd = ["python3", SERVER_SCRIPT]
        with open(LOG_FILE, "ab") as lf:
            process = subprocess.Popen(
                cmd,
                stdout=lf,
                stderr=subprocess.STDOUT,
                cwd=Path.cwd(),
                env=os.environ.copy(),
            )
            pid = process.pid
            # persist pid
            PID_FILE.write_text(str(pid))
            logger.info(f"Started MCP server (pid={pid}), logs -> {LOG_FILE}")
            return {"message": "MCP server started", "pid": pid}
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mcp/stop")
async def stop_mcp_server():
    pid = read_pid()
    if not pid or not is_running(pid):
        return {"message": "MCP server not running"}

    try:
        os.kill(pid, signal.SIGTERM)
        # wait for process to terminate
        time_waited = 0
        while is_running(pid) and time_waited < 5:
            time.sleep(0.5)
            time_waited += 0.5
        if is_running(pid):
            os.kill(pid, signal.SIGKILL)

        # remove pid file
        try:
            PID_FILE.unlink()
        except Exception:
            pass
        logger.info(f"Stopped MCP server (pid={pid})")
        return {"message": "MCP server stopped", "pid": pid}
    except Exception as e:
        logger.error(f"Failed to stop MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def tail_file(path: Path, interval: float = 0.5):
    """Yield appended lines from file (simple tail -f)"""
    if not path.exists():
        yield "event: log\n"
        yield "data: " + "\n\n"
        return

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        # go to end of file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(interval)
                continue
            yield f"data: {line.strip()}\n\n"


@router.get("/mcp/logs/stream")
async def stream_mcp_logs():
    # Server-Sent Events stream
    async def event_generator():
        loop = asyncio.get_event_loop()
        # run blocking generator in thread
        for chunk in tail_file(LOG_FILE):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/mcp/logs")
async def get_logs():
    if not LOG_FILE.exists():
        return {"logs": ""}
    text = LOG_FILE.read_text(errors="ignore")
    return {"logs": text}
