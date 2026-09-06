# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Standard Library — IO Extended v1.0
Erweiterte IO-Operationen.
Standard: ATC-97
"""

import os
import json
import time

class ATCIOExt:
    """Erweiterte IO-Funktionen."""

    # ── Konsole ──────────────────────────────────────
    @staticmethod
    def eprint(*args):
        import sys
        print(*args, file=sys.stderr)

    @staticmethod
    def input_line(prompt: str = "") -> str:
        return input(prompt)

    @staticmethod
    def input_int(prompt: str = "") -> int:
        return int(input(prompt))

    @staticmethod
    def input_float(prompt: str = "") -> float:
        return float(input(prompt))

    # ── Dateisystem ──────────────────────────────────
    @staticmethod
    def file_copy(src: str, dst: str):
        import shutil
        shutil.copy2(src, dst)

    @staticmethod
    def file_move(src: str, dst: str):
        import shutil
        shutil.move(src, dst)

    @staticmethod
    def file_size(path: str) -> int:
        return os.path.getsize(path)

    @staticmethod
    def file_modified(path: str) -> float:
        return os.path.getmtime(path)

    @staticmethod
    def dir_list(path: str = ".") -> list:
        return os.listdir(path)

    @staticmethod
    def dir_walk(path: str = ".") -> list:
        result = []
        for root, dirs, files in os.walk(path):
            for f in files:
                result.append(os.path.join(root, f))
        return result

    @staticmethod
    def dir_remove(path: str):
        os.rmdir(path)

    @staticmethod
    def path_join(*parts) -> str:
        return os.path.join(*parts)

    @staticmethod
    def path_split(path: str) -> tuple:
        return os.path.split(path)

    @staticmethod
    def path_ext(path: str) -> str:
        return os.path.splitext(path)[1]

    # ── JSON ─────────────────────────────────────────
    @staticmethod
    def json_load(path: str) -> any:
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def json_save(path: str, data, indent: int = 2):
        with open(path, "w") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def json_pretty(data, indent: int = 2) -> str:
        return json.dumps(data, indent=indent)

    # ── Zeit ─────────────────────────────────────────
    @staticmethod
    def now() -> float:
        return time.time()

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def sleep(seconds: float):
        time.sleep(seconds)

    @staticmethod
    def format_time(ts: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return time.strftime(fmt, time.localtime(ts))

    # ── Environment ──────────────────────────────────
    @staticmethod
    def env_get(key: str, default: str = None) -> str:
        return os.environ.get(key, default)

    @staticmethod
    def env_set(key: str, value: str):
        os.environ[key] = value

    @staticmethod
    def cwd() -> str:
        return os.getcwd()
