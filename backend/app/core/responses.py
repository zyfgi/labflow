from typing import Any


def ok(data: Any = None, message: str = "success") -> dict:
    return {"data": data, "message": message}


def paged(items: list, total: int, page: int, page_size: int, message: str = "success") -> dict:
    return {
        "data": {"items": items, "total": total, "page": page, "page_size": page_size},
        "message": message,
    }
