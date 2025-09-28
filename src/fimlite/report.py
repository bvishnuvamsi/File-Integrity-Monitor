from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

def _project_root() -> Path:
    # .../src/fimlite/report.py -> parents[2] = project root
    return Path(__file__).resolve().parents[2]

def _rel_href(from_file: Path, to_path_str: str | None) -> str | None:
    if not to_path_str:
        return None
    try:
        to_path = Path(to_path_str).resolve()
        base = from_file.parent.resolve()
        return os.path.relpath(to_path, base)
    except Exception:
        # fall back to original (may still render as text)
        return to_path_str

def render_report(
    out_html: Path,
    scan_id: int,
    started_at: str,
    ended_at: str,
    changes: List[Dict[str, Any]],
    counts: Dict[str, int],
    template_name: str = "report.html.j2",
) -> Path:
    """
    Render an HTML report to 'out_html'.
    - changes: list of dicts with keys like path, change_type, severity, diff_path
    - counts:  dict with total/added/removed/modified/diffs
    """
    templates_dir = _project_root() / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template(template_name)

    # make diff links relative to the HTML file location
    changes_view = []
    for c in changes:
        c2 = dict(c)  # shallow copy
        c2["diff_href"] = _rel_href(out_html, c.get("diff_path"))
        changes_view.append(c2)

    html = tpl.render(
        scan_id=scan_id,
        started_at=started_at,
        ended_at=ended_at,
        counts=counts,
        changes=changes_view,
    )

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return out_html
