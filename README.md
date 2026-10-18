# BTC spot order book heatmap study

Do order book "walls" (the bright bands on liquidity heatmaps like CoinGlass)
mark where Bitcoin price turns? Tested with pre-registered rules on 91 free
Tardis.dev days of Coinbase BTC-USD full order book data.

**Short answer: no.** Colored bands bounced less than ordinary levels, and
price did not turn just ahead of them either. See FINDINGS.md.

## Files
- PREREG.md: every test's rules, written before running (Amendments 1-5)
- FINDINGS.md: results, the bug that was caught and fixed, takeaways
- tardis_convert.py: downloads free Tardis days, rebuilds 1-minute snapshots
- coinbase_book_recorder.py: live recorder for the main test (in progress)
- score_pilot.py, score_pulls.py, score_tiers.py, score_approach.py: scorers
- patch_dist.py: the measurement fix (Amendment 3)
- plot_heatmap.py: draws a heatmap from recorded data
- *_events.csv: every scored touch/approach, for checking

## Reproduce
pip install pandas numpy plotly websockets
python tardis_convert.py --all
python score_tiers.py
python score_approach.py

Raw data is not included; tardis_convert.py rebuilds it.
