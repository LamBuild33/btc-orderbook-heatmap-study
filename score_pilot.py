"""
Score the Tardis pilot exactly as written in PREREG.md (Amendment 1).
Run:  python score_pilot.py
Reads heatmap_data_tardis/*.csv, prints the verdict, saves pilot_events.csv.
"""
import glob, os
import numpy as np
import pandas as pd

DATA_DIR = "heatmap_data_tardis"
MIN_OPEN = 20_000        # skip days that opened below this price
BAND_PCT = 0.0025        # band width ~0.25% of the day's opening price
TYPICAL_RANGE = 0.03     # typical size = median band within +/-3% of price
WALL_X = 3.0             # wall: >= 3x typical size
ORDINARY_X = 1.5         # ordinary: < 1.5x typical size
HOLD_MIN = 360           # wall must hold 6 hours
MAX_MISSING = 0.05
MAX_DIST = 0.05          # Amendment 3: only bands within 5% of price       # up to 5% of those minutes may be missing
WIN_START, WIN_END = 6 * 60, 18 * 60   # touches counted 06:00-18:00 UTC
BOUNCE_MIN = 360         # 6-hour bounce window
AWAY, THROUGH = 0.01, 0.005

def score_day(path):
    df = pd.read_csv(path, parse_dates=["time_utc"])
    day = df["time_utc"].dt.normalize().iloc[0]
    mid_s = df.drop_duplicates("time_utc").set_index("time_utc")["mid"].sort_index()
    open_px = mid_s.iloc[0]
    if open_px < MIN_OPEN:
        return None, None
    W = max(50, round(open_px * BAND_PCT / 50) * 50)
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
            near = np.abs(centers - mid[t]) <= mid[t] * TYPICAL_RANGE
            if near.any():
                typical[t] = np.median(sizes[t, near])
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sizes / typical[:, None]
    inrange = np.abs(centers[None, :] - mid[:, None]) <= mid[:, None] * MAX_DIST
    big = (ratio >= WALL_X) & present[:, None] & inrange
    wall_ok = np.zeros_like(big)
    need = int(np.ceil(HOLD_MIN * (1 - MAX_MISSING)))
    cs_big = np.vstack([np.zeros(len(bands)), np.cumsum(big, axis=0)])
    cs_pres = np.concatenate([[0], np.cumsum(present)])
    for t in range(HOLD_MIN - 1, 1440):
        n_pres = cs_pres[t + 1] - cs_pres[t + 1 - HOLD_MIN]
        if n_pres >= need:
            n_big = cs_big[t + 1] - cs_big[t + 1 - HOLD_MIN]
            wall_ok[t] = n_big == n_pres
    ordinary = (ratio < ORDINARY_X) & present[:, None] & inrange
    lo, hi = bands, bands + W
    dist = np.where(mid[:, None] < lo, lo - mid[:, None],
                    np.where(mid[:, None] > hi, mid[:, None] - hi, 0.0))
    near = (dist <= W / 2) & ~np.isnan(mid)[:, None]
    events = []
    for j, b in enumerate(bands):
        for t in range(max(WIN_START, 1), WIN_END):
            if not (near[t, j] and not near[t - 1, j]):
                continue
            p = mid[t - 1]
            if np.isnan(p):
                continue
            if wall_ok[t - 1, j]:
                kind = "wall"
            elif ordinary[t - 1, j]:
                kind = "ordinary"
            else:
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
            events.append(dict(date=day.date(), year=day.year, band=b, band_width=W,
                               kind=kind, side=side, touch_utc=minutes[t], bounce=bounce))
            break
    gone = total = 0
    for j in range(len(bands)):
        q = np.where(wall_ok[WIN_START:WIN_END, j])[0]
        if len(q) == 0:
            continue
        total += 1
        t0 = WIN_START + q[0]
        arrive = np.where(near[t0:WIN_END, j])[0]
        end = t0 + (arrive[0] if len(arrive) else WIN_END - t0)
        if (present[t0:end] & inrange[t0:end, j] & (ratio[t0:end, j] < ORDINARY_X)).any():
            gone += 1
    return events, (gone, total)

def rate(s):
    return 100 * s.mean() if len(s) else float("nan")

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    all_events, gone, total, used = [], 0, 0, 0
    for f in files:
        ev, vanish = score_day(f)
        if ev is None:
            continue
        used += 1
        all_events += ev
        gone += vanish[0]
        total += vanish[1]
    ev = pd.DataFrame(all_events)
    print(f"Days scored: {used} of {len(files)} (others opened below ${MIN_OPEN:,})")
    if ev.empty or (ev["kind"] == "wall").sum() == 0:
        print("No wall touches found.")
        return
    ev.to_csv("pilot_events.csv", index=False)
    walls, ords = ev[ev.kind == "wall"], ev[ev.kind == "ordinary"]
    wr, orr = rate(walls.bounce), rate(ords.bounce)
    gap = wr - orr
    print(f"\nWall touches: {len(walls)}   bounce rate {wr:.1f}%")
    print(f"Ordinary touches: {len(ords)}   bounce rate {orr:.1f}%")
    print(f"Gap: {gap:+.1f} points")
    print("\nBy year (years with 5+ wall touches count toward the verdict):")
    win_years = lose_years = counted = 0
    for y, g in ev.groupby("year"):
        w, o = g[g.kind == "wall"], g[g.kind == "ordinary"]
        flag = ""
        if len(w) >= 5:
            counted += 1
            if rate(w.bounce) > rate(o.bounce):
                win_years += 1
                flag = "walls better"
            else:
                lose_years += 1
                flag = "walls NOT better"
        print(f"  {y}: walls {len(w):>3} at {rate(w.bounce):5.1f}%   "
              f"ordinary {len(o):>4} at {rate(o.bounce):5.1f}%   {flag}")
    print("\nBy side (walls only):")
    for s, g in walls.groupby("side"):
        print(f"  {s} walls: {len(g)} touches, bounce {rate(g.bounce):.1f}%")
    if total:
        print(f"\nWalls that disappeared before price reached them: {gone} of {total} "
              f"({100*gone/total:.0f}%)")
    print("\nVERDICT (pre-registered rules):")
    if len(walls) < 30:
        print(f"  TOO SMALL: only {len(walls)} wall touches (need 30).")
    elif gap >= 15 and counted and win_years > counted / 2:
        print("  CONFIRMED")
    elif gap < 5 or (counted and lose_years > counted / 2):
        print("  REJECTED")
    else:
        print("  INCONCLUSIVE")
    print(f"  (gap {gap:+.1f} pts; walls better in {win_years} of {counted} counted years)")
    print("\nEvery touch is saved in pilot_events.csv")

if __name__ == "__main__":
    main()
