# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::IO
Input/Output für ATCLang. Context-isoliert.
ATC-94 | Sprint 2.5
"""
import os
from typing import Any, Optional


class ATCIO:
    """ATC::IO — Console, File, Network (context-isoliert)."""

    # ── Console ──────────────────────────────────

    @staticmethod
    def print(*args) -> None:
        """Print to console. Gas: 5"""
        print(*args)

    @staticmethod
    def println(*args) -> None:
        """Print with newline. Gas: 5"""
        print(*args)

    @staticmethod
    def format(template: str, *args) -> str:
        """Format string with args. Gas: 10"""
        return template.format(*args)

    # ── File (Node context only) ─────────────────

    @staticmethod
    def file_write(path: str, data: str) -> bool:
        """Write file. Gas: 50. Node context only."""
        try:
            with open(path, 'w') as f:
                f.write(str(data))
            return True
        except Exception:
            return False

    @staticmethod
    def file_read(path: str) -> Optional[str]:
        """Read file. Gas: 50. Node context only."""
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    def file_exists(path: str) -> bool:
        """Check file exists. Gas: 10"""
        return os.path.exists(path)

    @staticmethod
    def file_append(path: str, data: str) -> bool:
        """Append to file. Gas: 50"""
        try:
            with open(path, 'a') as f:
                f.write(str(data))
            return True
        except Exception:
            return False

    @staticmethod
    def file_delete(path: str) -> bool:
        """Delete file. Gas: 50"""
        try:
            os.remove(path)
            return True
        except Exception:
            return False

    # ── Directory ────────────────────────────────

    @staticmethod
    def dir_create(path: str) -> bool:
        """Create directory. Gas: 50"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def dir_list(path: str) -> list:
        """List directory. Gas: 20"""
        try:
            return os.listdir(path)
        except Exception:
            return []

    # ── Network (Node context only) ──────────────

    @staticmethod
    def net_send(host: str, port: int, data: str) -> bool:
        """Send network packet. Gas: 50. Node context only."""
        # Stub — real implementation in ATCLang Network module
        return False

    @staticmethod
    def net_recv(port: int) -> Optional[str]:
        """Receive network packet. Gas: 50. Node context only."""
        # Stub — real implementation in ATCLang Network module
        return None
