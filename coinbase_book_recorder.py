"""
Coinbase BTC-USD order book recorder.
Saves a summary of the order book once a minute to heatmap_data/<date>.csv
Run:  python coinbase_book_recorder.py   (Ctrl+C to stop)
"""
import asyncio, csv, json, math, os, time
from datetime import datetime, timezone
import websockets

URL = "wss://advanced-trade-ws.coinbase.com"
PRODUCT = "BTC-USD"
BUCKET = 50          # dollars per price row (the chart can merge these further)
RANGE_PCT = 0.10     # only keep orders within +/-10% of the current price
EVERY = 60           # seconds between saved snapshots
REFRESH = 3600       # reconnect every hour to get a fresh full order book
OUT_DIR = "heatmap_data"

bids = {}  # price -> BTC waiting to buy
asks = {}  # price -> BTC waiting to sell

def apply_updates(updates):
    for u in updates:
        price = float(u["price_level"])
        qty = float(u["new_quantity"])
        book = bids if u["side"] == "bid" else asks
        if qty == 0:
            book.pop(price, None)
        else:
            book[price] = qty

def save_snapshot():
    if not bids or not asks:
        return
    best_bid, best_ask = max(bids), min(asks)
    if best_bid >= best_ask:
        raise ConnectionError("order book out of sync")
    mid = (best_bid + best_ask) / 2
    lo, hi = mid * (1 - RANGE_PCT), mid * (1 + RANGE_PCT)
    rows = {}
    for p, q in bids.items():
        if p >= lo:
            rows.setdefault(math.floor(p / BUCKET) * BUCKET, [0.0, 0.0])[0] += q
    for p, q in asks.items():
        if p <= hi:
            rows.setdefault(math.floor(p / BUCKET) * BUCKET, [0.0, 0.0])[1] += q
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    path = os.path.join(OUT_DIR, now.strftime("%Y-%m-%d") + ".csv")
    is_new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["time_utc", "mid", "bucket", "bid_btc", "ask_btc"])
        for b, (bq, aq) in sorted(rows.items()):
            w.writerow([stamp, round(mid, 2), b, round(bq, 6), round(aq, 6)])
    print(f"{stamp} UTC  saved {len(rows)} price rows  price ${mid:,.2f}")

async def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    while True:
        try:
            async with websockets.connect(URL, max_size=None, ping_interval=20) as ws:
                for channel in ("level2", "heartbeats"):
                    await ws.send(json.dumps({"type": "subscribe",
                                              "product_ids": [PRODUCT],
                                              "channel": channel}))
                print("Connected to Coinbase. Recording...")
                bids.clear(); asks.clear()
                connected_at = time.time()
                next_save = time.time() + EVERY
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("channel") == "l2_data":
                        for ev in msg.get("events", []):
                            if ev.get("type") == "snapshot":
                                bids.clear(); asks.clear()
                            apply_updates(ev.get("updates", []))
                    if time.time() >= next_save:
                        save_snapshot()
                        next_save += EVERY
                    if time.time() - connected_at > REFRESH:
                        print("Hourly refresh, reconnecting...")
                        break
        except Exception as e:
            print(f"Connection problem: {e} -- retrying in 5 seconds")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Stopped.")
