"""Publish complete local results without replacing an existing export."""
import csv
import io
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime
from uuid import uuid4


def csv_cell(value):
    text = str(value)
    # Spreadsheet importers can ignore leading spaces/control characters.
    candidate = text.lstrip(" \t\r\n\v\f\ufeff")
    if candidate.startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def serialize(data, fmt):
    if fmt == "json":
        return json.dumps(data, indent=4, ensure_ascii=False, default=str)
    if fmt == "txt":
        if isinstance(data, dict):
            return "".join(f"{key}: {value}\n" for key, value in data.items())
        return str(data)
    if fmt == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        if isinstance(data, dict):
            rows = [("Key", "Value"), *data.items()]
        elif isinstance(data, list):
            rows = (row if isinstance(row, (list, tuple)) else [row] for row in data)
        else:
            rows = [[data]]
        for row in rows:
            writer.writerow([csv_cell(cell) for cell in row])
        return output.getvalue()
    raise ValueError(f"Format d'export inconnu : {fmt}")


def write_result(directory, filename, data, fmt="json"):
    content = serialize(data, fmt)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(filename)).strip("._") or "result"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=directory, prefix=".bluefox-", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link publication is atomic and fails if the destination exists.
        # Unlike replace(), it cannot overwrite a concurrent export. A filesystem
        # without hard links fails explicitly; never fall back to a partial write.
        for _ in range(10):
            destination = directory / f"{safe_name}_{timestamp}_{uuid4().hex}.{fmt}"
            try:
                os.link(temporary, destination)
            except FileExistsError:
                continue
            return str(destination)
        raise FileExistsError("Impossible de réserver un nom d'export unique")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def is_report(data):
    return isinstance(data, dict) and (
        data.get("report_kind") == "bluefox_investigation"
        or (data.get("title") == "BlueFox OSINT Investigation Report"
            and isinstance(data.get("sections"), list))
    )


def report_text(report):
    lines = ["=" * 60, "  BLUEFOX OSINT INVESTIGATION REPORT",
             f"  Généré: {report['generated']}", f"  Outil: {report['tool']}", "=" * 60]

    def append(value, indent=2):
        if isinstance(value, dict):
            for key, item in value.items():
                lines.append(f"{' ' * indent}{key}:")
                append(item, indent + 4)
        elif isinstance(value, list):
            for item in value:
                append(item, indent + 4)
        else:
            lines.append(f"{' ' * indent}{value}")

    for section in report["sections"]:
        lines.extend(["", "─" * 60, f"  SOURCE: {section['source_file']}", "─" * 60])
        append(section["data"])
    return "\n".join(lines) + "\n"
