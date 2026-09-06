# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Collections
Datenstrukturen für ATCLang Smart Contracts.
ATC-94 | Sprint 2.5
"""
from typing import Any, Dict, List, Set, Optional, Iterator


class ATCCollections:
    """ATC::Collections — Map, Array, Set, Queue, Stack."""

    # ── Map (Ordered Dict) ───────────────────────

    @staticmethod
    def map_new() -> Dict:
        """Create empty Map. Gas: 10"""
        return {}

    @staticmethod
    def map_get(m: Dict, key: Any) -> Any:
        """Get value by key. Gas: 5"""
        return m.get(key)

    @staticmethod
    def map_set(m: Dict, key: Any, value: Any) -> Dict:
        """Set key-value. Gas: 5"""
        m[key] = value
        return m

    @staticmethod
    def map_delete(m: Dict, key: Any) -> Dict:
        """Delete key. Gas: 5"""
        if key in m:
            del m[key]
        return m

    @staticmethod
    def map_contains(m: Dict, key: Any) -> bool:
        """Check key exists. Gas: 5"""
        return key in m

    @staticmethod
    def map_keys(m: Dict) -> List:
        """Get all keys. Gas: 5"""
        return list(m.keys())

    @staticmethod
    def map_values(m: Dict) -> List:
        """Get all values. Gas: 5"""
        return list(m.values())

    @staticmethod
    def map_size(m: Dict) -> int:
        """Map size. Gas: 2"""
        return len(m)

    # ── Array (List) ─────────────────────────────

    @staticmethod
    def array_new() -> List:
        """Create empty Array. Gas: 10"""
        return []

    @staticmethod
    def array_push(arr: List, value: Any) -> List:
        """Append value. Gas: 5"""
        arr.append(value)
        return arr

    @staticmethod
    def array_pop(arr: List) -> Any:
        """Remove and return last. Gas: 5"""
        if not arr:
            return None
        return arr.pop()

    @staticmethod
    def array_get(arr: List, idx: int) -> Any:
        """Get by index. Gas: 3"""
        if 0 <= idx < len(arr):
            return arr[idx]
        return None

    @staticmethod
    def array_set(arr: List, idx: int, value: Any) -> List:
        """Set by index. Gas: 3"""
        if 0 <= idx < len(arr):
            arr[idx] = value
        return arr

    @staticmethod
    def array_len(arr: List) -> int:
        """Array length. Gas: 2"""
        return len(arr)

    @staticmethod
    def array_contains(arr: List, value: Any) -> bool:
        """Check value exists. Gas: 5"""
        return value in arr

    @staticmethod
    def array_slice(arr: List, start: int, end: int) -> List:
        """Slice array. Gas: 5"""
        return arr[start:end]

    @staticmethod
    def array_reverse(arr: List) -> List:
        """Reverse array. Gas: 10"""
        return arr[::-1]

    @staticmethod
    def array_sort(arr: List, reverse: bool = False) -> List:
        """Sort array. Gas: 20"""
        return sorted(arr, reverse=reverse)

    # ── Set ──────────────────────────────────────

    @staticmethod
    def set_new() -> Set:
        """Create empty Set. Gas: 10"""
        return set()

    @staticmethod
    def set_add(s: Set, value: Any) -> Set:
        """Add value. Gas: 5"""
        s.add(value)
        return s

    @staticmethod
    def set_contains(s: Set, value: Any) -> bool:
        """Check value exists. Gas: 5"""
        return value in s

    @staticmethod
    def set_remove(s: Set, value: Any) -> Set:
        """Remove value. Gas: 5"""
        s.discard(value)
        return s

    @staticmethod
    def set_size(s: Set) -> int:
        """Set size. Gas: 2"""
        return len(s)

    @staticmethod
    def set_union(a: Set, b: Set) -> Set:
        """Union. Gas: 10"""
        return a | b

    @staticmethod
    def set_intersection(a: Set, b: Set) -> Set:
        """Intersection. Gas: 10"""
        return a & b

    @staticmethod
    def set_difference(a: Set, b: Set) -> Set:
        """Difference. Gas: 10"""
        return a - b

    # ── Queue (FIFO) ─────────────────────────────

    @staticmethod
    def queue_new() -> List:
        """Create empty Queue. Gas: 10"""
        return []

    @staticmethod
    def queue_enqueue(q: List, value: Any) -> List:
        """Add to back. Gas: 5"""
        q.append(value)
        return q

    @staticmethod
    def queue_dequeue(q: List) -> Any:
        """Remove from front. Gas: 5"""
        if not q:
            return None
        return q.pop(0)

    @staticmethod
    def queue_peek(q: List) -> Any:
        """Peek front. Gas: 3"""
        return q[0] if q else None

    @staticmethod
    def queue_size(q: List) -> int:
        """Queue size. Gas: 2"""
        return len(q)

    # ── Stack (LIFO) ─────────────────────────────

    @staticmethod
    def stack_new() -> List:
        """Create empty Stack. Gas: 10"""
        return []

    @staticmethod
    def stack_push(s: List, value: Any) -> List:
        """Push onto stack. Gas: 5"""
        s.append(value)
        return s

    @staticmethod
    def stack_pop(s: List) -> Any:
        """Pop from stack. Gas: 5"""
        if not s:
            return None
        return s.pop()

    @staticmethod
    def stack_peek(s: List) -> Any:
        """Peek top. Gas: 3"""
        return s[-1] if s else None

    @staticmethod
    def stack_size(s: List) -> int:
        """Stack size. Gas: 2"""
        return len(s)
