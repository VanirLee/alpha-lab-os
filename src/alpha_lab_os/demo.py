from __future__ import annotations

import math
import random
import time
from pathlib import Path

from .storage import Store


def seed_demo(path: str | Path, periods: int = 12, tokens: int = 6) -> dict[str, int]:
    rng = random.Random(7)
    now = int(time.time() * 1000) - periods * 300000
    with Store(path) as store:
        run_id = "synthetic-demo"
        for period in range(periods):
            observed = now + period * 300000
            rows = []
            for index in range(tokens):
                drift = (index - 2.5) * 0.004 + (0.006 if period % 3 == 0 and index < 3 else -0.002)
                price = 1.0 + index * 0.07 + period * drift + rng.uniform(-0.002, 0.002)
                buy = 1000 + index * 250 + (400 if index < 3 else 0) + rng.uniform(-50, 50)
                sell = 900 + index * 190 + rng.uniform(-50, 50)
                rows.append({"binanceChainId": "56", "tokenContractAddress": f"0x{index + 1:040x}", "symbol": f"T{index+1}", "price": price, "priceChange5M": drift * 100, "priceChange1H": drift * 400, "volume5M": buy + sell, "buyVolume5M": buy, "sellVolume5M": sell, "txs5M": 40 + index, "liquidity": 100000 + index * 30000, "marketCap": 1000000 + index * 100000, "holders": 1000 + index * 100})
            store.add_market_rows(run_id, observed, rows)
            for amount, rate in ((100, 0.998), (500, 0.994), (1000, 0.987)):
                store.add_quote_rows(run_id, observed, {"chain": "56", "from_token": "0x0000000000000000000000000000000000000001", "to_token": "0x0000000000000000000000000000000000000002"}, str(amount), type("Response", (), {"latency_ms": 18.0, "body": {"code": 0}})(), [{"toTokenAmount": str(amount * rate), "vendorName": "demo-router", "quoteId": f"demo-{period}-{amount}", "priceImpactPercent": str((1 - rate) * 100)}])
        store.commit()
        return store.counts()

