from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from .features import market_feature_row, number


def _rank(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for position, index in enumerate(order):
        ranks[index] = float(position + 1)
    return ranks


def _pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) < 2 or len(x) != len(y):
        return None
    mx, my = sum(x) / len(x), sum(y) / len(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    return sum(a * b for a, b in zip(dx, dy)) / den if den else None


def spearman(x: Iterable[Any], y: Iterable[Any]) -> float | None:
    pairs = [(number(a), number(b)) for a, b in zip(x, y)]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    return _pearson(_rank([a for a, _ in pairs]), _rank([b for _, b in pairs]))


def _forward_returns(rows: Sequence[Mapping[str, Any]], horizon_ms: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for raw in rows:
        row = market_feature_row(raw)
        if row.get("chain") is not None and row.get("token") is not None and number(row.get("observed_at_ms")) is not None and number(row.get("price")) not in (None, 0):
            groups[(str(row["chain"]), str(row["token"]))].append(row)
    output: list[dict[str, Any]] = []
    for series in groups.values():
        series = sorted(series, key=lambda item: int(float(item["observed_at_ms"])))
        for index, row in enumerate(series):
            start_ts, start_price = int(float(row["observed_at_ms"])), float(row["price"])
            future = next((candidate for candidate in series[index + 1:] if int(float(candidate["observed_at_ms"])) >= start_ts + horizon_ms and number(candidate.get("price")) not in (None, 0)), None)
            if future:
                enriched = dict(row)
                enriched["future_return"] = math.log(float(future["price"]) / start_price)
                output.append(enriched)
    return output


def cross_sectional_rank_ic(rows: Sequence[Mapping[str, Any]], horizons_seconds: Sequence[int] = (300, 3600)) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "INSUFFICIENT_DATA", "horizons": {}}
    factors = ("return_5m_pct", "ofi_5m", "volume_5m", "liquidity", "holders")
    for horizon in horizons_seconds:
        enriched = _forward_returns(rows, int(horizon) * 1000)
        by_time: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
        for row in enriched:
            by_time[int(float(row["observed_at_ms"]))].append(row)
        factor_stats: dict[str, Any] = {}
        for factor in factors:
            values: list[float] = []
            for batch in by_time.values():
                if len(batch) >= 3:
                    values.append(spearman([item.get(factor) for item in batch], [item.get("future_return") for item in batch]))
            values = [value for value in values if value is not None]
            factor_stats[factor] = {"n_periods": len(values), "mean_rank_ic": sum(values) / len(values) if values else None, "status": "ok" if values else "INSUFFICIENT_DATA"}
        result["horizons"][str(horizon)] = {"n_forward_rows": len(enriched), "n_cross_sections": sum(len(batch) >= 3 for batch in by_time.values()), "factors": factor_stats}
        if enriched:
            result["status"] = "OK"
    return result


def quote_curve(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("amount_out") not in (None, ""):
            groups[(str(row.get("chain")), str(row.get("from_token")), str(row.get("to_token")))].append(row)
    curves = []
    for key, group in groups.items():
        points = []
        for row in sorted(group, key=lambda item: float(item["amount_in"])):
            amount, output = float(row["amount_in"]), float(row["amount_out"])
            points.append({"amount_in": row["amount_in"], "amount_out": row["amount_out"], "effective_rate": output / amount if amount else None, "price_impact_percent": row.get("price_impact_percent"), "vendor": row.get("vendor"), "quote_id_present": bool(row.get("quote_id"))})
        rates = [float(item["effective_rate"]) for item in points if item["effective_rate"] is not None]
        slope = None
        if len(rates) >= 2 and rates[0] != 0:
            slope = (rates[-1] / rates[0] - 1) * 10000
        curves.append({"chain": key[0], "from_token": key[1], "to_token": key[2], "points": points, "impact_slope_bps_end_to_start": slope, "capacity_note": "Slope is a quote-curve diagnostic; normalize decimals and costs before treating as executable capacity."})
    return {"status": "OK" if curves else "INSUFFICIENT_DATA", "curves": curves}


def markout_stats(records: Sequence[Mapping[str, Any]], horizons: Sequence[str] = ("30s", "1m", "5m")) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for horizon in horizons:
        values = [number(row.get(horizon, row.get(f"markout_{horizon}"))) for row in records]
        values = [value for value in values if value is not None]
        result[horizon] = {"n": len(values), "mean": sum(values) / len(values) if values else None, "median": sorted(values)[len(values) // 2] if values else None, "win_rate": sum(value > 0 for value in values) / len(values) if values else None, "status": "OK" if values else "INSUFFICIENT_DATA"}
    return result


def analyze(rows: Sequence[Mapping[str, Any]], quote_rows: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    return {"schema_version": "0.1", "status": "OK" if rows else "INSUFFICIENT_DATA", "point_in_time_rule": "Only fields present in each observed snapshot are used; current state is never backfilled into the past.", "cross_sectional_rank_ic": cross_sectional_rank_ic(rows), "quote_curve": quote_curve(quote_rows)}

