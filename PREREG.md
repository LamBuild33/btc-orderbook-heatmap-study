# Pre-registration: Do spot order book walls hold?

Locked: 2026-10-17, before looking at any results.
Rule: if anything below changes after seeing data, it is a NEW test, not this one.

## Question
When price reaches a big buy or sell wall on Coinbase BTC-USD spot that has
held for 6+ hours, does price bounce off it more often than at ordinary levels?

## Data
- Source: my recorder (coinbase_book_recorder.py), 1-minute snapshots,
  $50 bands merged into $100 bands.
- Window: first snapshot (2026-10-17 06:55 UTC) through 2026-11-28 (6 weeks).
- Gaps (PC asleep/off) are allowed; log any gap longer than 2 hours.

## Definitions
- Typical band size: the median BTC across all $100 bands within +/-3% of price,
  at that minute.
- Wall: a band holding at least 3x the typical band size in every snapshot
  for the previous 6 hours (up to 5% of minutes may be missing).
- Ordinary level (comparison): a band under 1.5x the typical size at that time.
- Touch: the first minute price comes within $50 of the band, after it qualifies.
  One touch per band per 24 hours.
- Bounce: after the touch, price moves 1% away from the band (up for a buy wall,
  down for a sell wall) BEFORE moving 0.5% through it, within 24 hours.
  Anything else counts as "no bounce".

## Prediction
Walls bounce at least 15 percentage points more often than ordinary levels.
(Example: walls 60%, ordinary 45% or lower.)

## How I'll judge it
- CONFIRMED: wall bounce rate is +15 points or more above ordinary levels, AND
  it holds in both halves of the window (weeks 1-3 and weeks 4-6) on its own.
- REJECTED: the gap is under +5 points, OR it flips direction in either half.
- INCONCLUSIVE: anything in between. Extend recording 4 weeks, once, then decide.
- Minimum: at least 30 wall touches. Fewer means keep recording.

## Reported but not judged
- Buy walls and sell walls shown separately.
- How many walls disappeared before price reached them (possible fake walls).

## If confirmed
Keep recording; move the recorder to an always-on cloud server.
## If rejected
Stop recording. Use CoinGlass's free heatmap for eyeballing only.

---

# Amendment 1: Pilot test on Tardis one-day samples

Added: 2026-10-17, before looking at any Tardis results.
This pilot is SEPARATE from the main test above. The main test on my own
recorder data still decides; the pilot is an early look.

## Data
- Folder: heatmap_data_tardis (free Tardis.dev days, first of each month).
- Only days where BTC opened at $20,000 or higher. Cheaper days are left out
  because $50 price rows are too wide relative to price back then.
- Each day is scored on its own. Nothing carries over between days.

## Changes from the main test (everything else stays the same)
- Band width: about 0.25% of that day's opening price, rounded to the nearest
  $50 (example: $80,000 price gives $200 bands).
- Touch: price comes within half a band width of the wall's band.
- A wall still needs 6 hours of holding, so walls can only qualify from 06:00 UTC.
- Bounce window is 6 hours instead of 24. Touches are only counted from
  06:00 to 18:00 UTC, so every touch gets its full 6 hours inside the day.
- Bounce is still: 1% away from the band before 0.5% through it.

## How I'll judge the pilot
- CONFIRMED: walls bounce +15 points or more above ordinary levels, AND walls
  beat ordinary levels in most calendar years that have 5+ wall touches.
- REJECTED: the gap is under +5 points, OR walls lose in most of those years.
- INCONCLUSIVE: anything in between.
- Minimum: 30 wall touches in total, or the pilot is reported as too small.

## Reported but not judged
- Results by calendar year.
- Buy walls and sell walls separately.
- How many walls disappeared before price reached them.

---

# Amendment 2: What happens after a wall gets pulled? (exploratory)

Added: 2026-10-18, before running this analysis.
Honest note: I have already seen HOW MANY walls vanished in the pilot (119 of 311),
but NOT what price did afterward. This is a new, exploratory question. A result
here is a lead to re-check on recorder data, not proof.

## Question
After a wall is pulled, does price reach that level within 6 hours more often
than it reaches an ordinary level the same distance away?

## Data
Same as Amendment 1: heatmap_data_tardis, days opening at $20,000+, same band
width (about 0.25% of the day's opening price), each day scored on its own.

## Definitions
- Wall: same as Amendment 1 (3x typical size, held 6 hours).
- Pulled: the first minute the wall's band drops below 1.5x typical size,
  while price has NOT yet come within half a band width of it.
  Only pulls between 06:00 and 18:00 UTC count, so each gets a full 6 hours.
  One pull per band per day (the first one).
- Matched ordinary level: at the same minute, on the same side of price, the
  ordinary band (under 1.5x typical) whose distance from price is closest to
  the pulled wall's distance, within one band width. If none exists, the
  event is skipped.
- Reached: price comes within half a band width of the level within 6 hours.

## Prediction
Pulled-wall levels get reached at least 10 percentage points more often than
matched ordinary levels.

## How I'll judge it
- CONFIRMED: gap is +10 points or more, AND pulled walls beat matched levels in
  most calendar years that have 10+ pull events.
- REJECTED: gap is under +3 points, OR pulled walls lose in most of those years.
- INCONCLUSIVE: anything in between.
- Minimum: 50 pull events in total, or report as too small.

## Reported but not judged
- Results by year, and buy walls vs sell walls separately.
- How often price went 0.5% THROUGH the level within the 6 hours.

---

# Amendment 3: Measurement fix (applies to Amendments 1 and 2)

Added: 2026-10-18, after finding a measurement error, before re-running.
Problem: the data only records orders within 10% of price. Bands near that edge
slide out of view as price moves, so they looked "pulled" when nobody cancelled
them. The pull test found pulled walls sitting a median ~11% from price.
This is a bug fix, not a rule tweak to get a better answer.

## Fix
- Walls, ordinary levels and matched levels only count while the band is
  within 5% of price at that minute.
- A wall counts as pulled or vanished only if it drops below 1.5x typical size
  while still within 5% of price.
- Everything else in Amendments 1 and 2 stays the same.

## Re-run
Both the pilot (Amendment 1) and the pull test (Amendment 2) are re-run with
this fix. The earlier "38% of walls vanished" and the pull-test zeros are
withdrawn as affected by the bug.

---

# Amendment 5: Does price turn just BEFORE colored bands? (exploratory)

Added: 2026-10-18, before running. Honest note: this idea came after seeing
Amendment 4 fail (bounces seemed to happen near bands, not on them). The
"turn before reaching" outcome has NOT been looked at yet. Result = lead only;
confirm later on recorder data.

## Same as Amendment 4
Data, band width (0.125% of open), 4H candles, in-view rule, and color tiers
(yellow 43%+, green 25-43%, grey 1/6-25%, ordinary under 1/6 of the biggest
band in the most recent completed candle).

## New definitions
- Approach: the first minute price comes within 0.3% of price of the band's
  near edge, while NOT yet within half a band width of it.
  Counted 04:00-18:00 UTC only. One approach per band per day.
- Turn before: after the approach, price moves 1% away from the band
  (up for a band below, down for a band above) BEFORE coming within half a
  band width of it, within 6 hours. Anything else = no turn.

## How I'll judge it
- CONFIRMED: colored bands get turn-befores +10 points or more above ordinary,
  AND rates go in order yellow >= green >= grey, AND colored beat ordinary in
  most calendar years with 10+ colored approaches.
- REJECTED: colored gap under +3 points, OR colored lose in most of those years.
- INCONCLUSIVE: anything in between.
- Minimum: 30 colored approaches, or report as too small.

## Reported but not judged
- Each tier's rate and count, by year, and buy vs sell side.
