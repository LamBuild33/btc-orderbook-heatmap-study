"""Amendment 3 patch: only count bands within 5% of price. Run once."""
import sys

COMMON = [
    ("MAX_MISSING = 0.05",
     "MAX_MISSING = 0.05\nMAX_DIST = 0.05          # Amendment 3: only bands within 5% of price"),
    ("    big = (ratio >= WALL_X) & present[:, None]\n",
     "    inrange = np.abs(centers[None, :] - mid[:, None]) <= mid[:, None] * MAX_DIST\n"
     "    big = (ratio >= WALL_X) & present[:, None] & inrange\n"),
    ("    ordinary = (ratio < ORDINARY_X) & present[:, None]\n",
     "    ordinary = (ratio < ORDINARY_X) & present[:, None] & inrange\n"),
]
EXTRA = {
    "score_pilot.py": [
        ("        if (~big[t0:end, j] & present[t0:end]).any():",
         "        if (present[t0:end] & inrange[t0:end, j] & (ratio[t0:end, j] < ORDINARY_X)).any():"),
    ],
    "score_pulls.py": [
        ("            if not (present[t] and ratio[t, j] < ORDINARY_X):",
         "            if not (present[t] and inrange[t, j] and ratio[t, j] < ORDINARY_X):"),
    ],
}

for name, extra in EXTRA.items():
    with open(name, encoding="utf-8-sig") as f:
        text = f.read()
    if "MAX_DIST" in text:
        print(f"{name}: already patched, skipping")
        continue
    for old, new in COMMON + extra:
        n = text.count(old)
        if n != 1:
            sys.exit(f"{name}: expected 1 match, found {n} for:\n{old}\nNothing was changed.")
        text = text.replace(old, new)
    with open(name, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{name}: patched")
