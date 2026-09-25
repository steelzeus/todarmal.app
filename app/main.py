import os
import json
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import data
from . import db as dbm

app = FastAPI(title="Todarmal Nation-Building")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.on_event("startup")
def _startup():
    dbm.init_db()


# ------------------------------------------------------------------ helpers

def get_state(conn):
    rows = conn.execute("SELECT key, value FROM game_state").fetchall()
    return {r["key"]: r["value"] for r in rows}


def require_not_frozen(conn):
    st = get_state(conn)
    if st.get("frozen") == "1":
        raise HTTPException(423, "The game is frozen. No further actions are accepted.")
    return st


def team_by_code(conn, code):
    row = conn.execute("SELECT * FROM teams WHERE access_code=?", (code,)).fetchone()
    if not row:
        raise HTTPException(401, "Unknown access code.")
    return row


def get_team_auth(x_team_code: str = Header(default=None)):
    if not x_team_code:
        raise HTTPException(401, "Missing X-Team-Code header.")
    conn = dbm.get_conn()
    try:
        team = team_by_code(conn, x_team_code)
        return dict(team)
    finally:
        conn.close()


def get_admin_auth(x_admin_password: str = Header(default=None)):
    if x_admin_password != data.ADMIN_PASSWORD:
        raise HTTPException(401, "Bad admin password.")
    return True


def total_capacity(conn, team_id):
    rows = conn.execute("SELECT level FROM factories WHERE team_id=?", (team_id,)).fetchall()
    return sum(data.FACTORY_BASE_CAPACITY + r["level"] * data.FACTORY_LEVEL_BONUS for r in rows)


def trade_capacity(tier):
    if tier <= 0:
        return data.TRADE_CAPACITY_BASE
    return data.TRADE_CAPACITY_TIERS[tier - 1][2]


def inv_get(conn, team_id, item_id):
    row = conn.execute("SELECT qty FROM inventory WHERE team_id=? AND item_id=?", (team_id, item_id)).fetchone()
    return row["qty"] if row else 0.0


def inv_add(conn, team_id, item_id, delta):
    cur = inv_get(conn, team_id, item_id)
    newv = cur + delta
    if newv < -1e-9:
        raise HTTPException(400, f"Not enough {item_id} (have {cur}, need {-delta}).")
    conn.execute(
        "INSERT INTO inventory (team_id, item_id, qty) VALUES (?, ?, ?) "
        "ON CONFLICT(team_id, item_id) DO UPDATE SET qty=?",
        (team_id, item_id, max(newv, 0), max(newv, 0)),
    )


def log(conn, team_id, kind, detail: dict):
    conn.execute("INSERT INTO event_log (team_id, kind, detail) VALUES (?, ?, ?)",
                 (team_id, kind, json.dumps(detail)))


def product_ref_value(product_id):
    p = data.PRODUCTS[product_id]
    return (p["sell_low"] + p["sell_high"]) / 2


def team_public_state(conn, team_row):
    team_id = team_row["id"]
    inv_rows = conn.execute("SELECT item_id, qty FROM inventory WHERE team_id=?", (team_id,)).fetchall()
    inventory = {r["item_id"]: r["qty"] for r in inv_rows if r["qty"] > 1e-9}
    prod_value = 0.0
    for item_id, qty in inventory.items():
        if item_id.startswith("prod:"):
            prod_value += qty * product_ref_value(item_id.split(":", 1)[1])
    factories = conn.execute("SELECT id, level FROM factories WHERE team_id=?", (team_id,)).fetchall()
    cap_total = total_capacity(conn, team_id)
    return {
        "id": team_id,
        "name": team_row["name"],
        "treasury": team_row["treasury"],
        "inventory": inventory,
        "factories": [{"id": f["id"], "level": f["level"], "capacity": data.FACTORY_BASE_CAPACITY + f["level"] * data.FACTORY_LEVEL_BONUS} for f in factories],
        "capacity_total": cap_total,
        "production_used": team_row["production_used"],
        "trade_tier": team_row["trade_tier"],
        "trade_capacity": trade_capacity(team_row["trade_tier"]),
        "trade_units_used": team_row["trade_units_used"],
        "round1_estimate": round(prod_value, 2),
    }


# ------------------------------------------------------------------ models

class ExtractReq(BaseModel):
    resource_id: str
    qty: float


class ProduceReq(BaseModel):
    product_id: str
    qty: float


class FactoryUpgradeReq(BaseModel):
    factory_id: int


class ListReq(BaseModel):
    item_id: str
    qty: float
    ask_price: float


class BuyReq(BaseModel):
    listing_id: int
    qty: float
    price: float | None = None


class AssignReq(BaseModel):
    team_id: int
    resources: list[str]
    crisis_id: str


class RoundReq(BaseModel):
    round: int


class EditTeamReq(BaseModel):
    team_id: int
    treasury: float | None = None


# ------------------------------------------------------------------ static reference data

@app.get("/api/reference")
def reference():
    return {
        "resources": {k: {"name": v[0], "extraction_cost": v[1]} for k, v in data.RESOURCES.items()},
        "products": data.PRODUCTS,
        "factory_level_cost": data.FACTORY_LEVEL_COST,
        "factory_bonus": data.FACTORY_LEVEL_BONUS,
        "base_capacity": data.BASE_CAPACITY,
        "new_factory_cost": data.NEW_FACTORY_COST,
        "trade_capacity_base": data.TRADE_CAPACITY_BASE,
        "trade_capacity_tiers": data.TRADE_CAPACITY_TIERS,
    }


# ------------------------------------------------------------------ team state

@app.get("/api/state")
def api_state(team=Depends(get_team_auth)):
    conn = dbm.get_conn()
    try:
        row = conn.execute("SELECT * FROM teams WHERE id=?", (team["id"],)).fetchone()
        st = get_state(conn)
        res_rows = conn.execute("SELECT resource_id FROM team_resources WHERE team_id=?", (team["id"],)).fetchall()
        crisis = data.CRISES.get(row["crisis_id"], {})
        out = team_public_state(conn, row)
        out["resources"] = [r["resource_id"] for r in res_rows]
        out["crisis"] = {"id": row["crisis_id"], **crisis}
        out["round"] = int(st.get("round", "1"))
        out["frozen"] = st.get("frozen") == "1"
        return out
    finally:
        conn.close()


@app.post("/api/extract")
def api_extract(req: ExtractReq, team=Depends(get_team_auth)):
    if req.qty <= 0:
        raise HTTPException(400, "Quantity must be positive.")
    conn = dbm.get_conn()
    try:
        st = require_not_frozen(conn)
        if st.get("round") != "1":
            raise HTTPException(400, "Extraction only happens in Round 1.")
        row = conn.execute("SELECT * FROM teams WHERE id=?", (team["id"],)).fetchone()
        owned = {r["resource_id"] for r in conn.execute(
            "SELECT resource_id FROM team_resources WHERE team_id=?", (team["id"],)).fetchall()}
        if req.resource_id not in owned:
            raise HTTPException(403, "Your country does not have access to this resource.")
        if req.resource_id not in data.RESOURCES:
            raise HTTPException(404, "Unknown resource.")
        cost = req.qty * data.RESOURCES[req.resource_id][1]
        if row["treasury"] < cost:
            raise HTTPException(400, f"Not enough treasury. Need {cost}, have {row['treasury']}.")
        conn.execute("UPDATE teams SET treasury = treasury - ? WHERE id=?", (cost, team["id"]))
        inv_add(conn, team["id"], f"res:{req.resource_id}", req.qty)
        log(conn, team["id"], "extract", {"resource": req.resource_id, "qty": req.qty, "cost": cost})
        conn.commit()
        return {"ok": True, "cost": cost}
    finally:
        conn.close()


@app.post("/api/produce")
def api_produce(req: ProduceReq, team=Depends(get_team_auth)):
    if req.qty <= 0:
        raise HTTPException(400, "Quantity must be positive.")
    conn = dbm.get_conn()
    try:
        st = require_not_frozen(conn)
        if st.get("round") != "1":
            raise HTTPException(400, "Production only happens in Round 1.")
        if req.product_id not in data.PRODUCTS:
            raise HTTPException(404, "Unknown product.")
        row = conn.execute("SELECT * FROM teams WHERE id=?", (team["id"],)).fetchone()
        cap_total = total_capacity(conn, team["id"])
        if row["production_used"] + req.qty > cap_total + 1e-9:
            remaining = max(cap_total - row["production_used"], 0)
            raise HTTPException(409, f"Capacity ceiling reached. Only {remaining} units of capacity left — "
                                      f"upgrade a factory or build a new one to keep producing.")
        product = data.PRODUCTS[req.product_id]
        # check & reserve inputs
        needs = []
        for item_id, per_unit in product["inputs"]:
            need = per_unit * req.qty
            have = inv_get(conn, team["id"], item_id)
            if have < need - 1e-9:
                raise HTTPException(400, f"Not enough {item_id.split(':', 1)[1]}: need {need}, have {have}.")
            needs.append((item_id, need))
        for item_id, need in needs:
            inv_add(conn, team["id"], item_id, -need)
        inv_add(conn, team["id"], f"prod:{req.product_id}", req.qty)
        energy_yield = product.get("energy_yield", 0) * req.qty
        if energy_yield:
            inv_add(conn, team["id"], "res:energy", energy_yield)
        conn.execute("UPDATE teams SET production_used = production_used + ? WHERE id=?", (req.qty, team["id"]))
        log(conn, team["id"], "produce", {"product": req.product_id, "qty": req.qty, "energy_yield": energy_yield})
        conn.commit()
        return {"ok": True, "energy_yield": energy_yield}
    finally:
        conn.close()


@app.post("/api/factory/build")
def api_factory_build(team=Depends(get_team_auth)):
    conn = dbm.get_conn()
    try:
        require_not_frozen(conn)
        row = conn.execute("SELECT * FROM teams WHERE id=?", (team["id"],)).fetchone()
        cost = data.NEW_FACTORY_COST
        if row["treasury"] < cost:
            raise HTTPException(400, f"Not enough treasury. Need {cost}, have {row['treasury']}.")
        conn.execute("UPDATE teams SET treasury = treasury - ? WHERE id=?", (cost, team["id"]))
        conn.execute("INSERT INTO factories (team_id, level) VALUES (?, 0)", (team["id"],))
        log(conn, team["id"], "factory_build", {"cost": cost})
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/factory/upgrade")
def api_factory_upgrade(req: FactoryUpgradeReq, team=Depends(get_team_auth)):
    conn = dbm.get_conn()
    try:
        require_not_frozen(conn)
        frow = conn.execute("SELECT * FROM factories WHERE id=? AND team_id=?", (req.factory_id, team["id"])).fetchone()
        if not frow:
            raise HTTPException(404, "Factory not found.")
        level = frow["level"]
        if level >= 3:
            raise HTTPException(400, "Factory is already at the maximum level.")
        next_level = level + 1
        cost = data.FACTORY_LEVEL_COST[next_level]
        trow = conn.execute("SELECT treasury FROM teams WHERE id=?", (team["id"],)).fetchone()
        if trow["treasury"] < cost:
            raise HTTPException(400, f"Not enough treasury. Need {cost}, have {trow['treasury']}.")
        conn.execute("UPDATE teams SET treasury = treasury - ? WHERE id=?", (cost, team["id"]))
        conn.execute("UPDATE factories SET level=? WHERE id=?", (next_level, req.factory_id))
        log(conn, team["id"], "factory_upgrade", {"factory_id": req.factory_id, "level": next_level, "cost": cost})
        conn.commit()
        return {"ok": True, "level": next_level}
    finally:
        conn.close()


@app.post("/api/trade_capacity/upgrade")
def api_trade_capacity_upgrade(team=Depends(get_team_auth)):
    conn = dbm.get_conn()
    try:
        require_not_frozen(conn)
        row = conn.execute("SELECT * FROM teams WHERE id=?", (team["id"],)).fetchone()
        tier = row["trade_tier"]
        if tier >= 3:
            raise HTTPException(400, "Already at the maximum trade capacity tier.")
        next_tier, cost, new_cap = data.TRADE_CAPACITY_TIERS[tier]
        if row["treasury"] < cost:
            raise HTTPException(400, f"Not enough treasury. Need {cost}, have {row['treasury']}.")
        conn.execute("UPDATE teams SET treasury = treasury - ?, trade_tier=? WHERE id=?", (cost, next_tier, team["id"]))
        log(conn, team["id"], "trade_capacity_upgrade", {"tier": next_tier, "cost": cost, "new_cap": new_cap})
        conn.commit()
        return {"ok": True, "tier": next_tier, "capacity": new_cap}
    finally:
        conn.close()


# ------------------------------------------------------------------ market (round 2)

@app.get("/api/market")
def api_market():
    conn = dbm.get_conn()
    try:
        rows = conn.execute(
            "SELECT ml.id, ml.team_id, t.name as team_name, ml.item_id, ml.qty, ml.ask_price "
            "FROM market_listings ml JOIN teams t ON t.id=ml.team_id WHERE ml.active=1 ORDER BY ml.id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.post("/api/market/list")
def api_market_list(req: ListReq, team=Depends(get_team_auth)):
    if req.qty <= 0 or req.ask_price < 0:
        raise HTTPException(400, "Invalid quantity or price.")
    conn = dbm.get_conn()
    try:
        st = require_not_frozen(conn)
        if st.get("round") != "2":
            raise HTTPException(400, "The market only opens in Round 2.")
        have = inv_get(conn, team["id"], req.item_id)
        if have < req.qty - 1e-9:
            raise HTTPException(400, f"Not enough {req.item_id} to list — have {have}.")
        inv_add(conn, team["id"], req.item_id, -req.qty)  # escrow
        cur = conn.execute(
            "INSERT INTO market_listings (team_id, item_id, qty, ask_price) VALUES (?, ?, ?, ?)",
            (team["id"], req.item_id, req.qty, req.ask_price),
        )
        log(conn, team["id"], "market_list", {"item_id": req.item_id, "qty": req.qty, "ask_price": req.ask_price})
        conn.commit()
        return {"ok": True, "listing_id": cur.lastrowid}
    finally:
        conn.close()


@app.post("/api/market/delist/{listing_id}")
def api_market_delist(listing_id: int, team=Depends(get_team_auth)):
    conn = dbm.get_conn()
    try:
        require_not_frozen(conn)
        row = conn.execute("SELECT * FROM market_listings WHERE id=? AND team_id=? AND active=1",
                           (listing_id, team["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Listing not found.")
        inv_add(conn, team["id"], row["item_id"], row["qty"])  # return escrow
        conn.execute("UPDATE market_listings SET active=0 WHERE id=?", (listing_id,))
        log(conn, team["id"], "market_delist", {"listing_id": listing_id})
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/market/buy")
def api_market_buy(req: BuyReq, team=Depends(get_team_auth)):
    if req.qty <= 0:
        raise HTTPException(400, "Quantity must be positive.")
    conn = dbm.get_conn()
    try:
        st = require_not_frozen(conn)
        if st.get("round") != "2":
            raise HTTPException(400, "The market only opens in Round 2.")
        listing = conn.execute("SELECT * FROM market_listings WHERE id=? AND active=1", (req.listing_id,)).fetchone()
        if not listing:
            raise HTTPException(404, "Listing not found or no longer active.")
        if listing["team_id"] == team["id"]:
            raise HTTPException(400, "You cannot buy your own listing.")
        if req.qty > listing["qty"] + 1e-9:
            raise HTTPException(400, f"Only {listing['qty']} available in this listing.")
        price = req.price if req.price is not None else listing["ask_price"]
        total_price = price * req.qty

        buyer = conn.execute("SELECT * FROM teams WHERE id=?", (team["id"],)).fetchone()
        seller = conn.execute("SELECT * FROM teams WHERE id=?", (listing["team_id"],)).fetchone()

        if buyer["treasury"] < total_price:
            raise HTTPException(400, f"Not enough treasury. Need {total_price}, have {buyer['treasury']}.")
        buyer_cap = trade_capacity(buyer["trade_tier"])
        if buyer["trade_units_used"] + req.qty > buyer_cap + 1e-9:
            raise HTTPException(409, f"This purchase would exceed your export/import capacity "
                                      f"({buyer['trade_units_used']}/{buyer_cap} used). Upgrade your trade capacity first.")
        seller_cap = trade_capacity(seller["trade_tier"])
        if seller["trade_units_used"] + req.qty > seller_cap + 1e-9:
            raise HTTPException(409, f"The seller's export/import capacity can't cover this sale "
                                      f"({seller['trade_units_used']}/{seller_cap} used). Ask them to upgrade first.")

        new_qty = listing["qty"] - req.qty
        conn.execute("UPDATE market_listings SET qty=?, active=? WHERE id=?",
                    (new_qty, 0 if new_qty <= 1e-9 else 1, listing["id"]))
        conn.execute("UPDATE teams SET treasury = treasury - ?, trade_units_used = trade_units_used + ? WHERE id=?",
                    (total_price, req.qty, buyer["id"]))
        conn.execute("UPDATE teams SET treasury = treasury + ?, trade_units_used = trade_units_used + ? WHERE id=?",
                    (total_price, req.qty, seller["id"]))
        inv_add(conn, buyer["id"], listing["item_id"], req.qty)
        conn.execute(
            "INSERT INTO trades (listing_id, buyer_team_id, seller_team_id, item_id, qty, price_total) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (listing["id"], buyer["id"], seller["id"], listing["item_id"], req.qty, total_price),
        )
        log(conn, buyer["id"], "trade_buy", {"listing_id": listing["id"], "item_id": listing["item_id"],
                                             "qty": req.qty, "total_price": total_price, "counterparty": seller["name"]})
        log(conn, seller["id"], "trade_sell", {"listing_id": listing["id"], "item_id": listing["item_id"],
                                               "qty": req.qty, "total_price": total_price, "counterparty": buyer["name"]})
        conn.commit()
        return {"ok": True, "total_price": total_price}
    finally:
        conn.close()


@app.get("/api/trades")
def api_trades():
    conn = dbm.get_conn()
    try:
        rows = conn.execute(
            "SELECT tr.*, b.name as buyer_name, s.name as seller_name FROM trades tr "
            "JOIN teams b ON b.id=tr.buyer_team_id JOIN teams s ON s.id=tr.seller_team_id "
            "ORDER BY tr.id DESC LIMIT 100"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ------------------------------------------------------------------ leaderboard

@app.get("/api/leaderboard")
def api_leaderboard():
    conn = dbm.get_conn()
    try:
        teams = conn.execute("SELECT * FROM teams ORDER BY id").fetchall()
        st = get_state(conn)
        out = []
        for t in teams:
            pub = team_public_state(conn, t)
            out.append({"id": t["id"], "name": t["name"], "treasury": t["treasury"],
                       "round1_estimate": pub["round1_estimate"]})
        out.sort(key=lambda x: x["round1_estimate"], reverse=True)
        return {"round": int(st.get("round", "1")), "frozen": st.get("frozen") == "1", "teams": out}
    finally:
        conn.close()


# ------------------------------------------------------------------ admin

@app.get("/api/admin/teams")
def admin_teams(_=Depends(get_admin_auth)):
    conn = dbm.get_conn()
    try:
        teams = conn.execute("SELECT * FROM teams ORDER BY id").fetchall()
        out = []
        for t in teams:
            pub = team_public_state(conn, t)
            res_rows = conn.execute("SELECT resource_id FROM team_resources WHERE team_id=?", (t["id"],)).fetchall()
            pub["resources"] = [r["resource_id"] for r in res_rows]
            pub["crisis_id"] = t["crisis_id"]
            pub["access_code"] = t["access_code"]
            out.append(pub)
        return out
    finally:
        conn.close()


@app.post("/api/admin/assign")
def admin_assign(req: AssignReq, _=Depends(get_admin_auth)):
    if len(req.resources) != 3:
        raise HTTPException(400, "A country must have exactly 3 resources.")
    for r in req.resources:
        if r not in data.RESOURCES:
            raise HTTPException(400, f"Unknown resource: {r}")
    if req.crisis_id not in data.CRISES:
        raise HTTPException(400, f"Unknown crisis: {req.crisis_id}")
    conn = dbm.get_conn()
    try:
        row = conn.execute("SELECT id FROM teams WHERE id=?", (req.team_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Team not found.")
        conn.execute("DELETE FROM team_resources WHERE team_id=?", (req.team_id,))
        for r in req.resources:
            conn.execute("INSERT INTO team_resources (team_id, resource_id) VALUES (?, ?)", (req.team_id, r))
        conn.execute("UPDATE teams SET crisis_id=? WHERE id=?", (req.crisis_id, req.team_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/admin/round")
def admin_round(req: RoundReq, _=Depends(get_admin_auth)):
    if req.round not in (1, 2):
        raise HTTPException(400, "Round must be 1 or 2.")
    conn = dbm.get_conn()
    try:
        conn.execute("UPDATE game_state SET value=? WHERE key='round'", (str(req.round),))
        conn.commit()
        return {"ok": True, "round": req.round}
    finally:
        conn.close()


@app.post("/api/admin/freeze")
def admin_freeze(_=Depends(get_admin_auth)):
    conn = dbm.get_conn()
    try:
        conn.execute("UPDATE game_state SET value='1' WHERE key='frozen'")
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/admin/unfreeze")
def admin_unfreeze(_=Depends(get_admin_auth)):
    conn = dbm.get_conn()
    try:
        conn.execute("UPDATE game_state SET value='0' WHERE key='frozen'")
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/admin/team/edit")
def admin_edit_team(req: EditTeamReq, _=Depends(get_admin_auth)):
    conn = dbm.get_conn()
    try:
        row = conn.execute("SELECT id FROM teams WHERE id=?", (req.team_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Team not found.")
        if req.treasury is not None:
            conn.execute("UPDATE teams SET treasury=? WHERE id=?", (req.treasury, req.team_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/audit/{team_id}")
def admin_audit(team_id: int, _=Depends(get_admin_auth)):
    conn = dbm.get_conn()
    try:
        row = conn.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Team not found.")
        pub = team_public_state(conn, row)
        res_rows = conn.execute("SELECT resource_id FROM team_resources WHERE team_id=?", (team_id,)).fetchall()
        pub["resources"] = [r["resource_id"] for r in res_rows]
        pub["crisis"] = {"id": row["crisis_id"], **data.CRISES.get(row["crisis_id"], {})}
        trades = conn.execute(
            "SELECT tr.*, b.name as buyer_name, s.name as seller_name FROM trades tr "
            "JOIN teams b ON b.id=tr.buyer_team_id JOIN teams s ON s.id=tr.seller_team_id "
            "WHERE tr.buyer_team_id=? OR tr.seller_team_id=? ORDER BY tr.id", (team_id, team_id)).fetchall()
        pub["trade_history"] = [dict(t) for t in trades]
        events = conn.execute("SELECT kind, detail, created_at FROM event_log WHERE team_id=? ORDER BY id",
                              (team_id,)).fetchall()
        pub["event_log"] = [dict(e) for e in events]
        return pub
    finally:
        conn.close()


@app.get("/api/admin/export")
def admin_export(_=Depends(get_admin_auth)):
    conn = dbm.get_conn()
    try:
        teams = conn.execute("SELECT * FROM teams ORDER BY id").fetchall()
        out = []
        for t in teams:
            pub = team_public_state(conn, t)
            res_rows = conn.execute("SELECT resource_id FROM team_resources WHERE team_id=?", (t["id"],)).fetchall()
            pub["resources"] = [r["resource_id"] for r in res_rows]
            pub["crisis"] = {"id": t["crisis_id"], **data.CRISES.get(t["crisis_id"], {})}
            out.append(pub)
        return out
    finally:
        conn.close()


@app.get("/api/admin/reset_all")
def admin_reset_warning():
    raise HTTPException(405, "Use POST /api/admin/reset with the admin password.")


@app.post("/api/admin/reset")
def admin_reset(_=Depends(get_admin_auth)):
    """Wipes ALL game data and re-seeds from data.py. Irreversible — for testing only."""
    conn = dbm.get_conn()
    try:
        for tbl in ["trades", "market_listings", "event_log", "inventory", "factories", "team_resources", "teams", "game_state"]:
            conn.execute(f"DELETE FROM {tbl}")
        conn.commit()
        dbm.seed(conn)
        return {"ok": True}
    finally:
        conn.close()


# ------------------------------------------------------------------ static frontend

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
