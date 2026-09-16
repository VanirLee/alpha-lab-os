from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Mapping


def render(report: Mapping[str, Any], counts: Mapping[str, int], latest: list[Mapping[str, Any]], output: str | Path) -> None:
    cards = "".join(f"<div class='card'><span>{html.escape(str(key))}</span><strong>{value}</strong></div>" for key, value in counts.items())
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(row.get(key, '')))}</td>" for key in ("observed_at_ms", "symbol", "price", "price_change_5m", "volume_5m", "liquidity", "holders")) + "</tr>" for row in latest)
    payload = html.escape(json.dumps(report, ensure_ascii=False))
    document = f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>Alpha Lab OS</title><style>body{{font:14px system-ui;background:#0e1320;color:#e8eef9;max-width:1200px;margin:32px auto;padding:0 20px}}h1{{font-size:28px}}.muted{{color:#97a4ba}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{background:#182235;border:1px solid #293752;border-radius:10px;padding:14px 18px;min-width:120px}}.card span{{display:block;color:#97a4ba;font-size:12px}}.card strong{{font-size:24px}}table{{width:100%;border-collapse:collapse;margin-top:22px;background:#141d2d}}th,td{{padding:9px;border-bottom:1px solid #293752;text-align:left}}th{{color:#9cc4ff}}pre{{white-space:pre-wrap;background:#141d2d;padding:14px;border-radius:8px}}</style><h1>Alpha Lab OS</h1><p class='muted'>Point-in-Time research dashboard · raw data remains in SQLite · synthetic data is explicitly marked in the report.</p><div class='cards'>{cards}</div><h2>Latest market state</h2><table><thead><tr><th>time</th><th>symbol</th><th>price</th><th>5m %</th><th>volume 5m</th><th>liquidity</th><th>holders</th></tr></thead><tbody>{rows or '<tr><td colspan=7>INSUFFICIENT_DATA</td></tr>'}</tbody></table><h2>Analysis</h2><pre>{payload}</pre></html>"""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")

