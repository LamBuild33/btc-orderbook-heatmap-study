"""
Score Amendment 2 in PREREG.md: what happens after a wall gets pulled?
Run:  python score_pulls.py
Reads heatmap_data_tardis/*.csv, prints the verdict, saves pull_events.csv.
"""
import glob, os
import numpy as np
import pandas as pd

DATA_DIR = "heatmap_data_tardis"
MIN_OPEN = 20_000
BAND_PCT = 0.0025
TYPICAL_RANGE = 0.03
WALL_X = 3.0
ORDINARY_X = 1.5
HOLD_MIN = 360
MAX_MISSING = 0.05
MAX_DIST = 0.05          # Amendment 3: only bands within 5% of price
WIN_START, WIN_END = 6 * 60, 18 * 60
LOOK_MIN = 360
THROUGH = 0.005

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
    mid = mid_s.reindex(minutes).to_numpy()
    centers = bands + W / 2
    typical = np.full(1440, np.nan)
    for t in range(1440):
        if present[t]:
            nb = np.abs(centers - mid[t]) <= mid[t] * TYPICAL_RANGE
            if nb.any():
                typical[t] = np.median(sizes[t, nb])
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sizes / typical[:, None]
    inrange = np.abs(centers[None, :] - mid[:, None]) <= mid[:, None] * MAX_DIST
    big = (ratio >= WALL_X) & present[:, None] & inrange
    ordinary = (ratio < ORDINARY_X) & present[:, None] & inrange
    wall_ok = np.zeros_like(big)
    need = int(np.ceil(HOLD_MIN * (1 - MAX_MISSING)))
    cs_big = np.vstack([np.zeros(len(bands)), np.cumsum(big, axis=0)])
    cs_pres = np.concatenate([[0], np.cumsum(present)])
    for t in range(HOLD_MIN - 1, 1440):
        n_pres = cs_pres[t + 1] - cs_pres[t + 1 - HOLD_MIN]
        if n_pres >= need:
            wall_ok[t] = (cs_big[t + 1] - cs_big[t + 1 - HOLD_MIN]) == n_pres
    lo, hi = bands, bands + W
    m = mid[:, None]
    dist = np.where(m < lo, lo - m, np.where(m > hi, m - hi, 0.0))
    near = (dist <= W / 2) & ~np.isnan(mid)[:, None]

    def outcome(k, t, side):
        seg = slice(t + 1, t + 1 + LOOK_MIN)
        reached = bool(near[seg, k].any())
        path = mid[seg]
        if side == "buy":
            through = bool((path <= lo[k] * (1 - THROUGH)).any())
        else:
            through = bool((path >= hi[k] * (1 + THROUGH)).any())
        return reached, through

    events = []
    for j in range(len(bands)):
        armed_since = None
        for t in range(HOLD_MIN, WIN_END):
            if armed_since is None and wall_ok[t - 1, j]:
                armed_since = t - 1
            if armed_since is None:
                continue
            if near[armed_since - HOLD_MIN + 1: t + 1, j].any():
                break
            if not (present[t] and inrange[t, j] and ratio[t, j] < ORDINARY_X):
                continue
            if t < WIN_START:
                break
            p = mid[t]
            side = "buy" if hi[j] <= p else ("sell" if lo[j] >= p else None)
            if side is None:
                break
            d = dist[t, j]
            same_side = (hi <= p) if side == "buy" else (lo >= p)
            cand = (ordinary[t] & same_side & ~near[t] & (np.abs(dist[t] - d) <= W))
            cand[j] = False
            if not cand.any():
                break
            idx = np.where(cand)[0]
            diffs = np.abs(dist[t, idx] - d)
            ties = idx[np.isclose(diffs, diffs.min())]
            r_p, th_p = outcome(j, t, side)
            outs = [outcome(k, t, side) for k in ties]
            r_m = float(np.mean([o[0] for o in outs]))
            th_m = float(np.mean([o[1] for o in outs]))
            events.append(dict(date=day.date(), year=day.year, side=side, band_width=W,
                               pull_utc=minutes[t], distance=round(d, 2),
                               pulled_band=bands[j],
                               matched_band="/".join(str(int(bands[k])) for k in ties),
                               pulled_reached=r_p, matched_reached=r_m,
                               pulled_through=th_p, matched_through=th_m))
            break
    return events

def pct(s):
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
        print("No pull events found.")
        return
    ev.to_csv("pull_events.csv", index=False)
    rp, rm = pct(ev.pulled_reached), pct(ev.matched_reached)
    gap = rp - rm
    print(f"\nPull events: {len(ev)}")
    print(f"Pulled-wall level reached within 6h:   {rp:.1f}%")
    print(f"Matched ordinary level reached:        {rm:.1f}%")
    print(f"Gap: {gap:+.1f} points")
    print("\nBy year (years with 10+ events count toward the verdict):")
    wins = losses = counted = 0
    for y, g in ev.groupby("year"):
        a, b = pct(g.pulled_reached), pct(g.matched_reached)
        flag = ""
        if len(g) >= 10:
            counted += 1
            if a > b:
                wins += 1
                flag = "pulled higher"
            else:
                losses += 1
                flag = "pulled NOT higher"
        print(f"  {y}: {len(g):>3} events   pulled {a:5.1f}%   matched {b:5.1f}%   {flag}")
    print("\nBy side:")
    for s, g in ev.groupby("side"):
        print(f"  {s} walls: {len(g)} events   pulled {pct(g.pulled_reached):.1f}%   "
              f"matched {pct(g.matched_reached):.1f}%")
    print(f"\nWent 0.5% THROUGH the level within 6h:  pulled {pct(ev.pulled_through):.1f}%   "
          f"matched {pct(ev.matched_through):.1f}%")
    print("\nVERDICT (pre-registered rules):")
    if len(ev) < 50:
        print(f"  TOO SMALL: only {len(ev)} pull events (need 50).")
    elif gap >= 10 and counted and wins > counted / 2:
        print("  CONFIRMED")
    elif gap < 3 or (counted and losses > counted / 2):
        print("  REJECTED")
    else:
        print("  INCONCLUSIVE")
    print(f"  (gap {gap:+.1f} pts; pulled higher in {wins} of {counted} counted years)")
    print("\nEvery event is saved in pull_events.csv")

if __name__ == "__main__":
    main()
