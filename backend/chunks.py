from typing import Iterable, List, Any


def iter_chunks(items: Iterable[Any], size: int = 5000):
    buf: List[Any] = []
    for it in items:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf
