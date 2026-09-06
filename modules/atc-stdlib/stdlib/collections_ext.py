# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Standard Library — Collections Extended v1.0
Erweiterte Collection-Operationen.
Standard: ATC-96
"""

class ATCCollectionsExt:
    """Erweiterte Collection-Funktionen."""

    # ── List-Operationen ─────────────────────────────
    @staticmethod
    def list_reverse(lst: list) -> list:
        return lst[::-1]

    @staticmethod
    def list_sort(lst: list, key=None, reverse: bool = False) -> list:
        return sorted(lst, key=key, reverse=reverse)

    @staticmethod
    def list_filter(lst: list, predicate) -> list:
        return [x for x in lst if predicate(x)]

    @staticmethod
    def list_map(lst: list, fn) -> list:
        return [fn(x) for x in lst]

    @staticmethod
    def list_reduce(lst: list, fn, initial=None) -> any:
        result = initial
        for x in lst:
            if result is None:
                result = x
            else:
                result = fn(result, x)
        return result

    @staticmethod
    def list_find(lst: list, predicate) -> any:
        for x in lst:
            if predicate(x):
                return x
        return None

    @staticmethod
    def list_find_index(lst: list, predicate) -> int:
        for i, x in enumerate(lst):
            if predicate(x):
                return i
        return -1

    @staticmethod
    def list_chunk(lst: list, size: int) -> list:
        return [lst[i:i+size] for i in range(0, len(lst), size)]

    @staticmethod
    def list_flatten(lst: list) -> list:
        result = []
        for item in lst:
            if isinstance(item, list):
                result.extend(item)
            else:
                result.append(item)
        return result

    @staticmethod
    def list_unique(lst: list) -> list:
        seen = set()
        result = []
        for x in lst:
            key = x if isinstance(x, (int, float, str, bool)) else id(x)
            if key not in seen:
                seen.add(key)
                result.append(x)
        return result

    @staticmethod
    def list_zip(*lists) -> list:
        return list(zip(*lists))

    @staticmethod
    def list_take(lst: list, n: int) -> list:
        return lst[:n]

    @staticmethod
    def list_drop(lst: list, n: int) -> list:
        return lst[n:]

    @staticmethod
    def list_count(lst: list, value) -> int:
        return lst.count(value)

    # ── Map-Operationen ──────────────────────────────
    @staticmethod
    def map_from_pairs(pairs: list) -> dict:
        return dict(pairs)

    @staticmethod
    def map_to_pairs(m: dict) -> list:
        return list(m.items())

    @staticmethod
    def map_filter(m: dict, predicate) -> dict:
        return {k: v for k, v in m.items() if predicate(k, v)}

    @staticmethod
    def map_merge(m1: dict, m2: dict) -> dict:
        result = m1.copy()
        result.update(m2)
        return result

    @staticmethod
    def map_invert(m: dict) -> dict:
        return {v: k for k, v in m.items()}

    @staticmethod
    def map_get_default(m: dict, key, default=None) -> any:
        return m.get(key, default)

    # ── Set-Operationen ──────────────────────────────
    @staticmethod
    def set_new(lst: list = None) -> set:
        return set(lst or [])

    @staticmethod
    def set_union(s1: set, s2: set) -> set:
        return s1 | s2

    @staticmethod
    def set_intersect(s1: set, s2: set) -> set:
        return s1 & s2

    @staticmethod
    def set_difference(s1: set, s2: set) -> set:
        return s1 - s2

    @staticmethod
    def set_symmetric_diff(s1: set, s2: set) -> set:
        return s1 ^ s2

    @staticmethod
    def set_is_subset(s1: set, s2: set) -> bool:
        return s1 <= s2
