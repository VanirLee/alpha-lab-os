import unittest

from alpha_lab_os.analytics import cross_sectional_rank_ic, quote_curve, spearman
from alpha_lab_os.features import ofi


class AnalyticsTests(unittest.TestCase):
    def test_ofi_and_spearman(self):
        self.assertAlmostEqual(ofi("75", "25"), 0.5)
        self.assertAlmostEqual(spearman([1, 2, 3], [10, 20, 30]), 1.0)

    def test_rank_ic_needs_forward_cross_sections(self):
        rows = []
        for timestamp in (1_000_000, 1_300_000):
            for index in range(3):
                rows.append({"chain": "56", "token": f"t{index}", "observed_at_ms": timestamp, "price": 1 + index + (0.2 * index if timestamp > 1_000_000 else 0), "price_change_5m": index, "buy_volume_5m": 10 + index, "sell_volume_5m": 5, "volume_5m": 15 + index, "liquidity": 100 + index, "holders": 10 + index})
        report = cross_sectional_rank_ic(rows, (300,))
        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["horizons"]["300"]["n_cross_sections"], 1)

    def test_quote_curve_is_explicitly_diagnostic(self):
        rows = [{"chain": "56", "from_token": "a", "to_token": "b", "amount_in": "100", "amount_out": "99", "vendor": "x"}, {"chain": "56", "from_token": "a", "to_token": "b", "amount_in": "1000", "amount_out": "900", "vendor": "x"}]
        curve = quote_curve(rows)["curves"][0]
        self.assertEqual(len(curve["points"]), 2)
        self.assertIn("normalize decimals", curve["capacity_note"])

