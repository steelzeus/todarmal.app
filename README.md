# Todarmal Nation-Building — game server

A working backend + frontend for Round 1 (build) and Round 2 (trade).
Rounds 3 and 4 are offline and judged by hand, as designed — the software's
only job is tracking commerce in Rounds 1–2 and handing you a clean audit
of everything each team did.

## What's built and tested

- 15 teams seeded automatically, each with 3 resources, 1,000 mohurs, a
  private crisis, and one manufacturing unit (35 capacity).
- **Round 1:** extract resources (costs mohurs/unit), manufacture any of the
  52 products in `app/data.py` (full multi-tier recipe chains, including
  products that need other products as inputs), hit your capacity ceiling,
  upgrade a factory (10/20/30 mohurs, +5 capacity) or build a new one (80
  mohurs).
- **Round 2:** list anything in your inventory on the market at your own
  price, another team buys it (after negotiating the real price in person —
  the buy button lets them enter the agreed price), export/import capacity
  works the same way as production capacity (default 10 units, upgrade in
  three tiers for +10/+20/+50).
- **Live leaderboard** from the start of Round 1 (estimated production
  value), switching to treasury once Round 2 opens — clearly labeled as an
  estimate, not the official score, since judging is manual.
- **Admin panel** (`/admin.html`): see every team's full state live, edit
  each country's 3 resources and crisis assignment, correct a treasury by
  hand, switch rounds, freeze the game, and pull a full audit (JSON) per
  team or for everyone — exactly what you need for the Round 3 position
  papers.
- Every write (extract, produce, trade, factory upgrade...) is validated
  server-side and wrapped in a database transaction, so teams typing fast on
  their phones can't desync the numbers or double-spend.

I ran a full simulated Round 1 → Round 2 playthrough against this exact
codebase (extraction, capacity ceilings, factory upgrades, a real trade
between two teams from two separate browser sessions, freeze, audit) before
handing it to you — see "What I did NOT get to" below for what's still
untested at real scale.

## Running it locally (to try it yourself before the event)

```bash
cd todarmal
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/` (team view) or
`http://localhost:8000/admin.html` (admin view, password in `app/data.py`
— **change `ADMIN_PASSWORD` before the event**).

Each team's login is a short access code (e.g. `VEL01`), auto-generated
per country — see them all in the admin panel's "All teams" table, or in
`app/data.py`'s `COUNTRIES` list.

The whole game state lives in one file, `todarmal.db` (SQLite), created
automatically on first run. Back it up by just copying that file.

## Before the event — what you must still do

1. **Country names.** All 15 countries currently show as `C1`–`C15` (both
   display name and login code) — that's the event team's finalized
   resource/crisis table, just without real names yet. Send me the names
   whenever they're settled and I'll drop them into `app/data.py` — it's a
   one-line-per-country edit, nothing else in the code needs to change.
2. **Change `ADMIN_PASSWORD`** in `app/data.py`.
3. **Sanity-check the extraction costs and recipes** in `app/data.py`
   against what you actually want — they're transcribed from our design
   chat, but it's the one file that fully controls the economy, so it's
   worth a final read-through.
4. **Decide the Round 1 reference prices** if you want the live leaderboard
   to mean something closer to your real judging criteria — right now it
   uses the midpoint of each product's `sell_low`/`sell_high` in
   `app/data.py`. This number is never the official score.

## What's been tested since the last handoff

- **The finalized 15-country resource/crisis table** (your team's own,
  not a draft) is seeded exactly — verified by dumping every team's
  resources and crisis straight from the database.
- **Concurrency / load:** fired 375 simultaneous requests from all 15
  teams at once (extract + read state, in parallel threads) — zero errors,
  and a strict after-the-fact integrity check confirmed every team's
  treasury exactly matches the sum of its logged extraction costs (no
  lost or duplicated writes under load).
- **Race condition on a scarce listing:** had 4 teams simultaneously try
  to buy more of a 10-unit listing than was available — confirmed no
  oversold units; the database transactions correctly serialize
  competing buyers instead of corrupting the listing.
- **Mobile viewport** (375px, iPhone-width): no horizontal overflow, all
  cards stack cleanly, tabs scroll horizontally instead of wrapping. Fixed
  one real issue found this way (tab labels wrapping awkwardly). Admin
  panel is usable on mobile but its "all teams" table is wide — it's meant
  for a laptop, not a phone, and I didn't optimize it further.

## What's still worth doing before the event

- **A load test from real devices on the real venue wifi**, not just
  simulated concurrent requests from one machine — that's the one thing I
  genuinely cannot substitute for you.
- **The trade flow is single-step, not two-phase** — a buyer clicks "Buy"
  and it executes immediately (after negotiating the price in person).
  Say the word if you'd rather have a request/seller-confirms step instead.
- **No visual polish pass** — this reuses a plain version of the earlier
  dashboard's color palette but is functional-first, not the shiny mockup
  quality of the prototype you showed your team.

## Deploying so 15 teams can reach it on the day

I can't expose a public URL from where I built this, but any of these get
you a live link in a few minutes:

- **Render.com** (probably fastest): New → Web Service → connect this
  folder as a repo (or upload as a zip via their Blueprint) → build
  command `pip install -r requirements.txt` → start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add a persistent
  disk if you want `todarmal.db` to survive a restart (or just don't
  restart the service during the event).
- **Railway.app**: same idea, detects Python automatically, add the same
  start command.
- **Your own VPS**: copy the folder up, run the same two commands as
  "Running it locally" but bind to `0.0.0.0`, and put it behind Caddy or
  nginx for a real domain + HTTPS (or just share the `http://<ip>:8000`
  link directly — fine for a one-day event on a trusted local network).

Either way, test it from an actual phone on the actual venue wifi before
the event, per the plan we discussed — that's the one thing I can't do
for you from here.
