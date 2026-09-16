from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .analytics import analyze
from .client import BinanceWeb3Client
from .collector import collect, dry_run_plan, load_config
from .config import Settings
from .dashboard import render
from .demo import seed_demo
from .storage import Store


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="alpha_lab")
    sub = p.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="local configuration checks")
    doctor.add_argument("--with-credentials", action="store_true")
    collect_cmd = sub.add_parser("collect", help="bounded read-only Binance Web3 snapshot")
    collect_cmd.add_argument("--config", default="configs/universe.json")
    collect_cmd.add_argument("--db", default="data/alpha_lab.db")
    collect_cmd.add_argument("--html", default="artifacts/alpha-latest.html")
    collect_cmd.add_argument("--dry-run", action="store_true")
    analyze_cmd = sub.add_parser("analyze", help="analyze a local point-in-time database")
    analyze_cmd.add_argument("--db", default="data/alpha_lab.db")
    analyze_cmd.add_argument("--html", default="artifacts/analysis.html")
    demo = sub.add_parser("demo", help="seed synthetic data and render a local report")
    demo.add_argument("--db", default="data/demo.db")
    demo.add_argument("--html", default="artifacts/demo.html")
    return p


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "doctor":
        settings = Settings.from_env(require_credentials=False)
        _print({"status": "PASS", "version": "0.1.0", "base_url": settings.base_url, "qps_cap": settings.qps, "credentials_present": bool(settings.api_key and settings.secret_key), "credentials_file_detected": settings.credentials_file, "network_called": False, "secret_values_printed": False})
        return 0
    if args.command == "demo":
        counts = seed_demo(args.db)
        with Store(args.db) as store:
            report = analyze(store.panel_rows(), store.query("SELECT * FROM quotes ORDER BY observed_at_ms, amount_in"))
            report["data_mode"] = "SYNTHETIC_DEMO_ONLY"
            render(report, counts, store.query("SELECT * FROM market_state ORDER BY observed_at_ms DESC LIMIT 12"), args.html)
        _print({"status": "COMPLETED", "data_mode": "SYNTHETIC_DEMO_ONLY", "db": str(Path(args.db).resolve()), "html": str(Path(args.html).resolve()), "counts": counts})
        return 0
    if args.command == "analyze":
        with Store(args.db) as store:
            counts = store.counts()
            report = analyze(store.panel_rows(), store.query("SELECT * FROM quotes ORDER BY observed_at_ms, amount_in"))
            render(report, counts, store.query("SELECT * FROM market_state ORDER BY observed_at_ms DESC LIMIT 30"), args.html)
        _print({"status": report["status"], "db": str(Path(args.db).resolve()), "html": str(Path(args.html).resolve()), "counts": counts})
        return 0
    if args.command != "collect":
        return 2
    config = load_config(args.config)
    if args.dry_run:
        _print(dry_run_plan(config))
        return 0
    try:
        settings = Settings.from_env()
        summary = collect(BinanceWeb3Client(settings), config, args.db)
    except Exception as exc:
        _print({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "network_effects": {"read_only": True, "broadcast": False}})
        return 1
    with Store(args.db) as store:
        report = analyze(store.panel_rows(), store.query("SELECT * FROM quotes ORDER BY observed_at_ms, amount_in"))
        report["collection"] = summary
        render(report, store.counts(), store.query("SELECT * FROM market_state ORDER BY observed_at_ms DESC LIMIT 30"), args.html)
    _print({"status": summary["status"], "db": str(Path(args.db).resolve()), "html": str(Path(args.html).resolve()), "summary": summary})
    return 0
