"""Tests for movers.pick. Run: py -3.13 -m unittest test_movers -v"""
import unittest
from movers import pick

T, R = '2026-09-10', '2026-09-09'


def s(ref_trend, now_trend, avg7=None, extra=None):
    d = {R: {'trend': ref_trend, 'avg7': avg7 or now_trend}, T: {'trend': now_trend, 'avg7': avg7 or now_trend}}
    d.update(extra or {})
    return d


class Pick(unittest.TestCase):
    def test_ranks_by_percent_and_splits_sign(self):
        series = {1: s(10, 12), 2: s(10, 15), 3: s(10, 8), 4: s(10, 10)}
        up, down, n = pick(series, T, R)
        self.assertEqual([r['pid'] for r in up], [2, 1])
        self.assertEqual([r['pid'] for r in down], [3])
        self.assertEqual(n, 4)

    def test_band_uses_reference_price(self):
        series = {1: s(4.99, 9), 2: s(20.01, 25), 3: s(5, 6)}
        up, _, n = pick(series, T, R)
        self.assertEqual([r['pid'] for r in up], [3]); self.assertEqual(n, 1)

    def test_guard_drops_single_sale_spikes(self):
        # Raikou HGSS19 case: trend 6.93 -> 63.38 while the 7-day average sat at 9.68
        series = {1: s(6.93, 63.38, avg7=9.68), 2: s(10, 11, avg7=10.8)}
        up, _, _ = pick(series, T, R)
        self.assertEqual([r['pid'] for r in up], [2])

    def test_liquidity_applies_only_with_seven_day_pairs(self):
        days = [f'2026-09-{d:02d}' for d in range(2, 11)]
        frozen = {d: {'trend': 10, 'avg7': 10} for d in days}; frozen[T] = {'trend': 12, 'avg7': 12}
        moving = {d: {'trend': 10 + i * 0.1, 'avg7': 10} for i, d in enumerate(days)}; moving[T] = {'trend': 12, 'avg7': 12}
        up, _, _ = pick({1: frozen, 2: moving}, T, days[-2])
        self.assertEqual([r['pid'] for r in up], [2])
        # with only two exports the liquidity rule is not applied
        up2, _, _ = pick({1: s(10, 12)}, T, R)
        self.assertEqual([r['pid'] for r in up2], [1])

    def test_missing_prices_are_skipped(self):
        series = {1: {T: {'trend': 12, 'avg7': 12}}, 2: s(None, 12), 3: s(10, None)}
        up, down, n = pick(series, T, R)
        self.assertEqual((up, down, n), ([], [], 0))


if __name__ == '__main__':
    unittest.main()
