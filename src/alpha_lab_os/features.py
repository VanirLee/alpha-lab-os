from __future__ import annotations

import math
from typing import Any, Mapping


def number(value: Any) -> float | None:
    try:
        if value in (None, "") or isinstance(value, bool):
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def ofi(buy_volume: Any, sell_volume: Any) -> float | None:
    buy, sell = number(buy_volume), number(sell_volume)
    if buy is None or sell is None or buy + sell == 0:
        return None
    return (buy - sell) / (buy + sell)


def market_feature_row(item: Mapping[str, Any]) -> dict[str, Any]:
    buy, sell = item.get("buy_volume_5m", item.get("buyVolume5M")), item.get("sell_volume_5m", item.get("sellVolume5M"))
    return {
        "chain": item.get("chain", item.get("binanceChainId")),
        "token": item.get("token", item.get("tokenContractAddress")),
        "observed_at_ms": item.get("observed_at_ms", item.get("time")),
        "price": number(item.get("price")),
        "return_5m_pct": number(item.get("price_change_5m", item.get("priceChange5M"))),
        "return_1h_pct": number(item.get("price_change_1h", item.get("priceChange1H"))),
        "volume_5m": number(item.get("volume_5m", item.get("volume5M"))),
        "buy_volume_5m": number(buy),
        "sell_volume_5m": number(sell),
        "ofi_5m": ofi(buy, sell),
        "liquidity": number(item.get("liquidity")),
        "market_cap": number(item.get("market_cap", item.get("marketCap"))),
        "holders": number(item.get("holders")),
        "point_in_time": True,
    }

