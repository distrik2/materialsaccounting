import csv
import io
from typing import Any

from flask import Response, request


def get_int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except Exception:
        return default


def paginate(query, per_page: int = 20):
    page = get_int_arg("page", 1)
    if page < 1:
        page = 1

    total = query.count()
    pages = (total + per_page - 1) // per_page
    items = query.limit(per_page).offset((page - 1) * per_page).all()

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }


def csv_response(filename: str, header: list[str], rows: list[list[Any]]):
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)

    data = buf.getvalue().encode("utf-8-sig")
    resp = Response(data, mimetype="text/csv; charset=utf-8")
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return resp
