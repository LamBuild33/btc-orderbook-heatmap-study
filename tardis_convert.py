"""
Download free Tardis.dev Coinbase BTC-USD order book days and convert them
into the same 1-minute snapshot format as coinbase_book_recorder.py.
Run:  python tardis_convert.py 2026-10-01            (one day)
      python tardis_convert.py --all                 (every free 1st-of-month day)
Output goes to heatmap_data_tardis/<date>.csv. The big download is deleted after.
"""
import argparse, csv, math, os, sys, time, urllib.request
from datetime import date
import pandas as pd

BUCKET = 50
RANGE_PCT = 0.10
OUT_DIR = "heatmap_data_tardis"
RAW_DIR = "tardis_raw"
URL = "https://datasets.tardis.dev/v1/coinbase/incremental_book_L2/{y}/{m:02d}/{d:02d}/BTC-USD.csv.gz"

def download(day, path):
    url = URL.format(y=day.year, m=day.month, d=day.day)
    start = time.time()
    with urllib.request.urlopen(url) as r, open(path, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total:
                print(f"\r  downloading {got/1e6:,.0f} / {total/1e6:,.0f} MB", end="")
    print(f"\r  downloaded {got/1e6:,.0f} MB in {time.time()-start:,.0f}s" + " " * 20)

def snapshot_rows(bids, asks):
    if not bids or not asks:
        return None, None
    best_bid, best_ask = max(bids), min(asks)
    if best_bid >= best_ask:
        return None, None
    mid = (best_bid + best_ask) / 2
    lo, hi = mid * (1 - RANGE_PCT), mid * (1 + RANGE_PCT)
    rows = {}
    for p, q in bids.items():
        if p >= lo:
            rows.setdefault(math.floor(p / BUCKET) * BUCKET, [0.0, 0.0])[0] += q
    for p, q in asks.items():
        if p <= hi:
            rows.setdefault(math.floor(p / BUCKET) * BUCKET, [0.0, 0.0])[1] += q
    return mid, rows

def convert(raw_path, out_path):
    bids, asks = {}, {}
    next_min = None
    prev_snap = False
    saved = skipped = 0
    start = time.time()
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "mid", "bucket", "bid_btc", "ask_btc"])
        reader = pd.read_csv(raw_path, usecols=["timestamp", "is_snapshot", "side", "price", "amount"],
                             chunksize=2_000_000)
        for chunk in reader:
            snap = chunk["is_snapshot"].astype(str).str.lower().eq("true").tolist()
            for ts, is_snap, side, price, amt in zip(chunk["timestamp"].tolist(), snap,
                                                     chunk["side"].tolist(),
                                                     chunk["price"].tolist(),
                                                     chunk["amount"].tolist()):
                minute = ts // 60_000_000  # timestamps are microseconds
                if next_min is None:
                    next_min = minute + 1
                while minute >= next_min:
                    mid, rows = snapshot_rows(bids, asks)
                    stamp = pd.Timestamp(next_min * 60, unit="s").strftime("%Y-%m-%d %H:%M:%S")
                    if rows is None:
                        skipped += 1
                    else:
                        for b, (bq, aq) in sorted(rows.items()):
                            w.writerow([stamp, round(mid, 2), b, round(bq, 6), round(aq, 6)])
                        saved += 1
                    next_min += 1
                if is_snap and not prev_snap:
                    bids.clear()
                    asks.clear()
                prev_snap = is_snap
                book = bids if side == "bid" else asks
                if amt == 0:
                    book.pop(price, None)
                else:
                    book[price] = amt
            print(f"\r  converting... {saved:,} minutes saved", end="")
    print(f"\r  converted: {saved:,} minutes saved, {skipped} skipped, {time.time()-start:,.0f}s" + " " * 10)

def free_days():
    today = date.today()
    y, m = 2019, 4
    while (y, m) <= (today.year, today.month):
        yield date(y, m, 1)
        m += 1
        if m == 13:
            y, m = y + 1, 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dates", nargs="*", help="YYYY-MM-DD (first of a month)")
    ap.add_argument("--all", action="store_true", help="every free first-of-month day")
    ap.add_argument("--keep", action="store_true", help="keep the big raw download")
    args = ap.parse_args()
    days = list(free_days()) if args.all else [date.fromisoformat(d) for d in args.dates]
    if not days:
        sys.exit("Give a date like 2026-10-01, or use --all")
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    for day in days:
        out = os.path.join(OUT_DIR, f"{day}.csv")
        if os.path.exists(out):
            print(f"{day}: already done, skipping")
            continue
        print(f"{day}:")
        raw = os.path.join(RAW_DIR, f"{day}.csv.gz")
        try:
            if not os.path.exists(raw):
                download(day, raw + ".part")
                os.replace(raw + ".part", raw)
            convert(raw, out + ".part")
            os.replace(out + ".part", out)
        except Exception as e:
            print(f"\n  FAILED: {e}")
            if os.path.exists(out + ".part"):
                os.remove(out + ".part")
            continue
        if not args.keep:
            os.remove(raw)
    print("All done.")

if __name__ == "__main__":
    main()
