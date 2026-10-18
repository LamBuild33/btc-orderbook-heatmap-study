# FINDINGS: Do spot order book walls mark turning points? (BTC)

Written: 2026-10-18. Rules for every test were written in PREREG.md BEFORE running.

## Data
- 91 free Tardis.dev days (1st of each month, Apr 2019 - Oct 2026), Coinbase
  BTC-USD spot, full order book, rebuilt into 1-minute snapshots ($50 rows,
  +/-10% of price). 66 days used (BTC opened at $20,000+).
- Live recorder (coinbase_book_recorder.py) running since 2026-10-17 for the
  main test (scored ~2026-11-28).

## Results
| Test | What it asked | Result | Verdict |
|---|---|---|---|
| A1 Pilot (6h-held 3x walls) | Do walls bounce more than ordinary levels? | 10 touches; walls 30.0% vs ordinary 35.3% | TOO SMALL |
| A2 Pulled walls | After a wall is pulled, does price go there? | 3 real pulls in 66 days | TOO SMALL |
| A4 CoinGlass color tiers | Do colored bands bounce more, yellow most? | 695 colored touches: 30.2% vs 36.4% ordinary; yellow 25.2% < green 29.9% < grey 35.8% | REJECTED |
| A5 Turn before the band | Does price turn just ahead of colored bands? | 730 colored approaches: 20.7% vs 24.6% ordinary; no size ordering | REJECTED |

Colored levels did worse than ordinary levels in 5 of 6 years in both A4 and A5.

## Bug found and fixed (A3)
Bands near the 10% recording edge slid out of view and looked "pulled".
Fix: only count bands within 5% of price. Withdrawn as bug-affected: the
early "38% of walls vanished" figure and the first pull-test zeros.
After the fix, only 7% (8 of 115) of 6h-held walls near price vanished.

## Plain takeaway
In this data, heatmap colors show WHERE orders sit, not WHERE price turns,
either on the band or just before it. Bigger bands held worse, not better.
Use the heatmap as a map only; give it no extra weight as confluence.

## Limits
- Coinbase data; I watch Binance on CoinGlass.
- Single-day samples, 6-hour outcome window.
- "Big bands get pushed through" is a new, untested idea.

## Still open
- Main test on recorder data (6h-held walls), due ~2026-11-28.
- Trade log column: wall none / spot / perp / both, plus turn before / at / past.
