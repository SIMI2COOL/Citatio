import io
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pandas as pd

MAX_CSV_FNAME = 255


def _get_run_search():
    """Import run_search so src/ is on path and sortgs is available (Vercel bundles includeFiles: src/**)."""
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    cwd = Path(os.getcwd())
    for base in (root, cwd, root.parent):
        s = base / "src"
        if (s / "sortgs" / "sortgs.py").exists():
            if str(s) not in sys.path:
                sys.path.insert(0, str(s))
            break
    else:
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
    from sortgs.sortgs import run_search  # noqa: E402
    return run_search


def _sanitize_filename(s: str) -> str:
    name = re.sub(r"[\s:]+", "_", s)[:MAX_CSV_FNAME]
    return name or "scholar_results"


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            return self._do_post_impl()
        except Exception as e:
            _json_response(self, 500, {"error": f"Server error: {type(e).__name__}: {str(e)}"})

    def _do_post_impl(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return _json_response(self, 400, {"error": "Invalid JSON body"})

        keyword = str(data.get("keyword", "")).strip()
        if not keyword:
            return _json_response(self, 400, {"error": "keyword is required"})

        exact_phrase = bool(data.get("exact_phrase", False))
        if exact_phrase:
            keyword = f"'{keyword}'"

        sortby = data.get("sortby", "Citations")
        if sortby not in ("Citations", "cit/year"):
            sortby = "Citations"

        start_year = data.get("start_year", None)
        end_year = data.get("end_year", None)
        try:
            start_year = int(start_year) if start_year is not None else None
        except Exception:
            start_year = None
        try:
            end_year = int(end_year) if end_year is not None else None
        except Exception:
            end_year = None

        langfilter = data.get("langfilter", None)
        if isinstance(langfilter, list) and len(langfilter) > 0:
            langfilter_val = [str(x) for x in langfilter]
        else:
            langfilter_val = "All"

        nresults = data.get("nresults", 100)
        try:
            nresults = int(nresults)
        except Exception:
            nresults = 100
        nresults = max(10, min(50, nresults))

        fmt = str(data.get("format", "xlsx")).lower()
        if fmt not in ("xlsx", "csv"):
            fmt = "xlsx"

        try:
            run_search = _get_run_search()
        except Exception as e:
            return _json_response(self, 500, {"error": f"Import failed: {type(e).__name__}: {str(e)}"})

        try:
            df = run_search(
                keyword=keyword,
                nresults=nresults,
                sortby=sortby,
                start_year=start_year,
                end_year=end_year,
                langfilter=langfilter_val,
                debug=False,
                allow_selenium=False,
            )
        except Exception as e:
            return _json_response(self, 502, {"error": f"Search failed: {str(e)}"})

        base_name = _sanitize_filename(keyword.replace("'", ""))
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")

        if fmt == "csv":
            buf = io.StringIO()
            df.to_csv(buf, encoding="utf-8", index=True)
            payload = buf.getvalue().encode("utf-8")
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition", f'attachment; filename="{base_name}.csv"'
            )
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # xlsx
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Results", index=True)
        payload = b.getvalue()
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.send_header(
            "Content-Disposition", f'attachment; filename="{base_name}.xlsx"'
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

