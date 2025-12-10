import asyncio
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
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
    # Check if already running via PID file
    pid = read_pid()
    if pid and is_running(pid):
        return {"message": "MCP server already running", "pid": pid}

    # Ensure log dir
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Start as subprocess using module mode to ensure package imports work
    try:
        cmd = [sys.executable, "-m", "mcp_server.server.mcp_server"]
        with open(LOG_FILE, "ab") as lf:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
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
    if not pid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="MCP server not running")

    try:
        os.kill(pid, signal.SIGTERM)
        # wait for process to exit
        for _ in range(20):
            if not is_running(pid):
                break
            time.sleep(0.2)
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return {"message": "MCP server stopped", "pid": pid}
    except ProcessLookupError:
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="MCP server not running")
    except Exception as e:
        logger.error(f"Error stopping MCP server (pid={pid}): {e}")
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
    # Server-Sent Events stream — async file tail using aiofiles so we don't
    # block the FastAPI event loop. This yields SSE `data:` frames for each
    # new line appended to the log file.
    async def event_generator():
        try:
            # Wait until log file exists
            while not LOG_FILE.exists():
                await asyncio.sleep(0.2)

            async with aiofiles.open(LOG_FILE, mode="r", encoding="utf-8", errors="ignore") as afp:
                # Move to EOF
                await afp.seek(0, os.SEEK_END)
                while True:
                    line = await afp.readline()
                    if not line:
                        # No new data — yield nothing but sleep to avoid busy loop
                        await asyncio.sleep(0.2)
                        continue
                    # Yield a valid SSE data frame
                    yield f"data: {line.strip()}\n\n"
        except asyncio.CancelledError:
            # Client disconnected — stop the generator
            return
        except Exception as e:
            # Surface error to client as SSE message and then stop
            yield f"data: ERROR: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/mcp/logs")
async def get_logs():
    if not LOG_FILE.exists():
        return {"logs": ""}
    text = LOG_FILE.read_text(errors="ignore")
    return {"logs": text}


@router.get("/mcp/calls")
async def get_mcp_call_count(minutes: Optional[int] = None, tool: Optional[str] = None):
    """Return the number of MCP tool calls recorded in the MCP server log.

    Optional query params:
    - `minutes`: only count calls in the last N minutes
    - `tool`: filter by tool name (e.g. `rag_search`)
    """
    if not LOG_FILE.exists():
        return {"count": 0, "minutes": minutes, "tool": tool}

    count = 0
    cutoff = None
    now = datetime.now()
    if minutes is not None:
        cutoff = now - timedelta(minutes=int(minutes))

    # Log timestamps are like: "2025-12-10 19:36:17,292 - mcp-rag-server - INFO - ..."
    ts_format = "%Y-%m-%d %H:%M:%S,%f"

    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "Handling tool call:" not in line:
                    continue

                if tool:
                    # log line contains: Handling tool call: <name> with arguments
                    if f"Handling tool call: {tool}" not in line:
                        continue

                if cutoff is not None:
                    try:
                        ts_str = line.split(" - ")[0].strip()
                        ts = datetime.strptime(ts_str, ts_format)
                        if ts >= cutoff:
                            count += 1
                    except Exception:
                        # if parsing fails, still count the entry to be conservative
                        count += 1
                else:
                    count += 1
    except Exception:
        return {"count": 0, "minutes": minutes, "tool": tool}

    return {"count": count, "minutes": minutes, "tool": tool}
