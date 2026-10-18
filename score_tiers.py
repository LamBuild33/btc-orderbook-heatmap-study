"""
Score Amendment 4 FINAL in PREREG.md: CoinGlass-matched color tiers.
Run:  python score_tiers.py
Reads heatmap_data_tardis/*.csv, prints the verdict, saves tier_events.csv.
"""
import glob, os
import numpy as np
import pandas as pd

DATA_DIR = "heatmap_data_tardis"
MIN_OPEN = 20_000
BAND_PCT = 0.00125            # ~$100 bands at $80k (merge level 10)
MAX_DIST = 0.05               # in view: within 5% of the candle's average price
CANDLE = 240                  # 4H candles
MIN_PRESENT = 0.95            # a candle needs 95% of its minutes recorded
YELLOW, GREEN, GREY = 0.43, 0.25, 1 / 6
WIN_START, WIN_END = 4 * 60, 18 * 60
BOUNCE_MIN = 360
AWAY, THROUGH = 0.01, 0.005
TIERS = ["yellow", "green", "grey", "ordinary"]

def score_day(path):
    df = pd.read_csv(path, parse_dates=["time_utc"])
    day = df["time_utc"].dt.normalize().iloc[0]
    mid_s = df.drop_duplicates("time_utc").set_index("time_utc")["mid"].sort_index()
    if mid_s.iloc[0] < MIN_OPEN:
        return None
    W = max(50, round(mid_s.iloc[0] * BAND_PCT / 50) * 50)
    df["band"] = (df["bucket"] // W) * W
    df["size"] = df["bid_btc"] + df["ask_btc"]
    minutes = pd.date_range(day, periods=1440, freq="min")
    grid = (df.groupby(["time_utc", "band"])["size"].sum()
              .unstack(fill_value=0.0).reindex(minutes))
    present = grid.notna().all(axis=1).to_numpy()
    sizes = grid.fillna(0.0).to_numpy()
    bands = grid.columns.to_numpy(dtype=float)
    centers = bands + W / 2
    mid = mid_s.reindex(minutes).to_numpy()
    n_candles = 1440 // CANDLE
    tier = np.full((n_candles, len(bands)), None, dtype=object)
    for c in range(n_candles):
        sl = slice(c * CANDLE, (c + 1) * CANDLE)
        pres = present[sl]
        if pres.sum() < CANDLE * MIN_PRESENT:
            continue
        avg = sizes[sl][pres].mean(axis=0)
        px = np.nanmean(mid[sl][pres])
        view = np.abs(centers - px) <= px * MAX_DIST
        if not view.any():
            continue
        biggest = avg[view].max()
        if biggest <= 0:
            continue
        share = avg / biggest
        t = np.where(share >= YELLOW, "yellow",
            np.where(share >= GREEN, "green",
            np.where(share >= GREY, "grey", "ordinary"))).astype(object)
        t[~view] = None
        tier[c] = t
    lo, hi = bands, bands + W
    m = mid[:, None]
    dist = np.where(m < lo, lo - m, np.where(m > hi, m - hi, 0.0))
    near = (dist <= W / 2) & ~np.isnan(mid)[:, None]
    events = []
    for j in range(len(bands)):
        for t in range(WIN_START, WIN_END):
            if not (near[t, j] and not near[t - 1, j]):
                continue
            p = mid[t - 1]
            k = tier[t // CANDLE - 1, j]
            if np.isnan(p) or k is None:
                break
            side = "buy" if hi[j] <= p else ("sell" if lo[j] >= p else None)
            if side is None:
                break
            path_px = mid[t + 1: t + 1 + BOUNCE_MIN]
            if side == "buy":
                win = np.where(path_px >= hi[j] * (1 + AWAY))[0]
                lose = np.where(path_px <= lo[j] * (1 - THROUGH))[0]
            else:
                win = np.where(path_px <= lo[j] * (1 - AWAY))[0]
                lose = np.where(path_px >= hi[j] * (1 + THROUGH))[0]
            bounce = len(win) > 0 and (len(lose) == 0 or win[0] < lose[0])
            events.append(dict(date=day.date(), year=day.year, band=bands[j], band_width=W,
                               tier=k, side=side, touch_utc=minutes[t], bounce=bounce))
            break
    return events

def rate(s):
    return 100 * s.mean() if len(s) else float("nan")

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    rows, used = [], 0
    for f in files:
        ev = score_day(f)
        if ev is None:
            continue
        used += 1
        rows += ev
    print(f"Days scored: {used} of {len(files)} (others opened below ${MIN_OPEN:,})")
    ev = pd.DataFrame(rows)
    if ev.empty:
        print("No touches found.")
        return
    ev["colored"] = ev["tier"] != "ordinary"
    ev.to_csv("tier_events.csv", index=False)
    print("\nBounce rate by tier:")
    tr = {}
    for k in TIERS:
        g = ev[ev.tier == k]
        tr[k] = rate(g.bounce)
        print(f"  {k:<9} {len(g):>5} touches   bounce {tr[k]:5.1f}%")
    col, ordn = ev[ev.colored], ev[~ev.colored]
    cr, orr = rate(col.bounce), rate(ordn.bounce)
    gap = cr - orr
    print(f"\nColored (grey+green+yellow): {len(col)} touches, bounce {cr:.1f}%")
    print(f"Ordinary:                    {len(ordn)} touches, bounce {orr:.1f}%")
    print(f"Gap: {gap:+.1f} points")
    in_order = all(not np.isnan(tr[k]) for k in ["yellow", "green", "grey"]) and \
        tr["yellow"] >= tr["green"] >= tr["grey"]
    print(f"Order yellow >= green >= grey: {'YES' if in_order else 'NO'}")
    print("\nBy year (years with 10+ colored touches count toward the verdict):")
    wins = losses = counted = 0
    short = {"yellow": "yel", "green": "grn", "grey": "gry", "ordinary": "ord"}
    for y, g in ev.groupby("year"):
        c, o = g[g.colored], g[~g.colored]
        flag = ""
        if len(c) >= 10:
            counted += 1
            if rate(c.bounce) > rate(o.bounce):
                wins += 1
                flag = "colored better"
            else:
                losses += 1
                flag = "colored NOT better"
        parts = "  ".join(f"{short[k]} {len(g[g.tier == k]):>3}/{rate(g[g.tier == k].bounce):5.1f}%"
                          for k in TIERS)
        print(f"  {y}: {parts}   {flag}")
    print("\nBy side (colored only):")
    for s, g in col.groupby("side"):
        print(f"  {s}: {len(g)} touches, bounce {rate(g.bounce):.1f}%")
    print("\nVERDICT (pre-registered rules):")
    if len(col) < 30:
        print(f"  TOO SMALL: only {len(col)} colored touches (need 30).")
    elif gap >= 10 and in_order and counted and wins > counted / 2:
        print("  CONFIRMED")
    elif gap < 3 or (counted and losses > counted / 2):
        print("  REJECTED")
    else:
        print("  INCONCLUSIVE")
    print(f"  (gap {gap:+.1f} pts; order {'held' if in_order else 'did not hold'}; "
          f"colored better in {wins} of {counted} counted years)")
    print("\nEvery touch is saved in tier_events.csv")

if __name__ == "__main__":
    main()
