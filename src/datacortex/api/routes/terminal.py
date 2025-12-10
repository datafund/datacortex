"""WebSocket terminal bridge for Claude Code."""

import asyncio
import os
import pty
import signal
import struct
import fcntl
import termios
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class TerminalSession:
    """Manages a PTY session connected to Claude Code."""

    def __init__(self):
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.running = False

    def start(self, cols: int = 120, rows: int = 30) -> bool:
        """Start Claude Code in a PTY."""
        if self.running:
            return True

        # Create PTY
        self.master_fd, slave_fd = pty.openpty()

        # Set terminal size
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

        # Fork process
        self.pid = os.fork()

        if self.pid == 0:
            # Child process
            os.setsid()
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            os.close(self.master_fd)
            os.close(slave_fd)

            # Set working directory
            datacore_root = os.environ.get("DATACORE_ROOT", os.path.expanduser("~/Data"))
            if os.path.exists(datacore_root):
                os.chdir(datacore_root)

            # Set TERM for color support
            os.environ["TERM"] = "xterm-256color"

            # Execute Claude Code
            os.execvp("claude", ["claude"])
        else:
            # Parent process
            os.close(slave_fd)
            self.running = True

            # Make master non-blocking
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            return True

    def resize(self, cols: int, rows: int):
        """Resize the terminal."""
        if self.master_fd:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    async def read(self) -> bytes:
        """Read output from PTY."""
        if not self.master_fd:
            return b""

        try:
            data = await asyncio.to_thread(self._read_nonblock)
            return data
        except Exception:
            return b""

    def _read_nonblock(self) -> bytes:
        """Non-blocking read from master fd."""
        try:
            return os.read(self.master_fd, 4096)
        except BlockingIOError:
            return b""
        except OSError:
            return b""

    def write(self, data: bytes):
        """Write input to PTY."""
        if self.master_fd:
            os.write(self.master_fd, data)

    def stop(self):
        """Stop the terminal session."""
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except Exception:
                pass

        if self.master_fd:
            try:
                os.close(self.master_fd)
            except Exception:
                pass

        self.running = False
        self.master_fd = None
        self.pid = None


# Global session storage (simple for now, could use session IDs)
_sessions: dict[str, TerminalSession] = {}


@router.websocket("")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for terminal communication."""
    await websocket.accept()

    session = TerminalSession()
    session_id = str(id(websocket))
    _sessions[session_id] = session

    try:
        # Wait for init message with terminal size
        init_data = await websocket.receive_json()
        cols = init_data.get("cols", 120)
        rows = init_data.get("rows", 30)

        # Start Claude Code
        session.start(cols, rows)

        # Bidirectional communication
        async def read_pty():
            """Read from PTY and send to WebSocket."""
            while session.running:
                data = await session.read()
                if data:
                    await websocket.send_bytes(data)
                else:
                    await asyncio.sleep(0.01)

        async def write_pty():
            """Read from WebSocket and write to PTY."""
            while session.running:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive(),
                        timeout=0.1
                    )

                    if "bytes" in message:
                        session.write(message["bytes"])
                    elif "text" in message:
                        # Handle JSON commands (resize, etc.)
                        import json
                        try:
                            cmd = json.loads(message["text"])
                            if cmd.get("type") == "resize":
                                session.resize(cmd.get("cols", 120), cmd.get("rows", 30))
                            elif cmd.get("type") == "input":
                                session.write(cmd.get("data", "").encode())
                        except json.JSONDecodeError:
                            # Plain text input
                            session.write(message["text"].encode())

                except asyncio.TimeoutError:
                    continue
                except WebSocketDisconnect:
                    break

        await asyncio.gather(read_pty(), write_pty())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Terminal error: {e}")
    finally:
        session.stop()
        _sessions.pop(session_id, None)
