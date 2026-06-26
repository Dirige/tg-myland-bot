import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
import config

def _clear_proxy():
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ.pop(k, None)

def get(path):
    _clear_proxy()
    req = urllib.request.Request(config.BASE_URL + path, headers={
        "Authorization": f"Bearer {config.USER_TOKEN}",
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def post(path, data=None):
    _clear_proxy()
    body = json.dumps(data).encode() if data else b""
    req = urllib.request.Request(config.BASE_URL + path, data=body, method="POST", headers={
        "Authorization": f"Bearer {config.USER_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=config.STEAL_TIMEOUT) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def get_currency():
    data = get(f"/api/item/inventory?player_id={config.PLAYER_ID}&item_ids%5B%5D=12&item_ids%5B%5D=13")
    grain, stone = 0, 0
    if data:
        for item in data:
            qty = item.get("quantity", 0)
            if item.get("item_id") == 12: grain += qty
            elif item.get("item_id") == 13: stone += qty
    return grain, stone

def get_chronicle(count=3):
    _clear_proxy()
    url = f"{config.BASE_URL}/api/common/chronicle?action_type=village&action_id={config.MAP_ID}&page=1&page_size={count}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {config.USER_TOKEN}", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return [f'{item.get("tick_format", {}).get("string", "?")} {item.get("text", "")}'
                    for item in data.get("items", [])]
    except Exception:
        return []

@dataclass
class FarmResult:
    game_time: str = ""
    lands: list = field(default_factory=list)
    harvested: int = 0
    harvested_grain: int = 0
    planted: int = 0
    stolen: int = 0
    stolen_grain: int = 0
    stealable: int = 0
    seeds: int = 0
    grain: int = 0
    stone: int = 0
    errors: list = field(default_factory=list)

def harvest_land(lid, crop_id):
    r = post(f"/api/land/crop/{config.PLAYER_ID}/{lid}/harvest", {"crop_id": crop_id})
    if r and "yield_harvested" in r:
        return True, r["yield_harvested"]
    return False, 0

def plant_land(lid):
    return post(f"/api/land/crop/{config.PLAYER_ID}/{lid}/sow",
                {"item_id": config.WHEAT_SEED_ID, "quantity": config.SOW_QTY}) is not None

def steal_from_land(lid, crop_id):
    r = post(f"/api/land/crop/{config.PLAYER_ID}/{lid}/steal", {"crop_id": crop_id})
    if r and "player_stolen" in r:
        return True, r["player_stolen"]
    return False, 0

def _scan_lands(result):
    my_chunk = get(f"/api/map/{config.MAP_ID}/land/chunk?x=80&y=6&w=3&h=3")
    if not my_chunk:
        result.errors.append("Cannot get land data")
        return
    my_lands = [l for l in my_chunk if l.get("owner_data", {}).get("player_id") == config.PLAYER_ID]
    for land in my_lands:
        lid = land["land_id"]
        crop = land.get("crop")
        info = {"id": lid, "x": land["x"], "y": land["y"]}
        if crop is None:
            info["status"] = "empty"
        else:
            status = crop.get("crop_status", "")
            remain = crop.get("second_mature", 999)
            if status in ("mature", "harvestable") or remain <= 0:
                info["status"] = "harvestable"
            else:
                info["status"] = "growing"
                info["remain_str"] = f"{remain // 3600}h"
        result.lands.append(info)

def _scan_seeds(result):
    inv = get(f"/api/item/inventory?player_id={config.PLAYER_ID}")
    if inv:
        for item in inv:
            if item.get("item_id") == config.WHEAT_SEED_ID:
                result.seeds = item.get("quantity", 0)
                break

def run_farm(auto_harvest=True, auto_plant=True, auto_steal=True):
    result = FarmResult()
    gt = get("/api/common/time")
    if gt: result.game_time = gt.get("string", "?")
    result.grain, result.stone = get_currency()
    my_chunk = get(f"/api/map/{config.MAP_ID}/land/chunk?x=80&y=6&w=3&h=3")
    if not my_chunk:
        result.errors.append("Cannot get land data")
        return result
    my_lands = [l for l in my_chunk if l.get("owner_data", {}).get("player_id") == config.PLAYER_ID]
    for land in my_lands:
        lid = land["land_id"]
        crop = land.get("crop")
        info = {"id": lid, "x": land["x"], "y": land["y"]}
        if crop is None:
            info["status"] = "empty"
            if auto_plant and plant_land(lid):
                info["status"] = "planted"
                result.planted += 1
        else:
            status = crop.get("crop_status", "")
            remain = crop.get("second_mature", 999)
            if status in ("mature", "harvestable") or remain <= 0:
                info["status"] = "harvestable"
                if auto_harvest:
                    ok, gained = harvest_land(lid, crop["crop_id"])
                    if ok:
                        info["status"] = "harvested"
                        result.harvested += 1
                        result.harvested_grain += gained
                        if plant_land(lid):
                            result.planted += 1
                    else:
                        result.errors.append(f"Harvest failed: Land {lid}")
            else:
                info["status"] = "growing"
                info["remain_str"] = f"{remain // 3600}h"
        result.lands.append(info)
    _scan_seeds(result)
    if auto_steal:
        chunk = get(f"/api/map/{config.MAP_ID}/land/chunk?x=70&y=0&w=30&h=30")
        if chunk:
            steals = [l for l in chunk if l.get("crop") and l["crop"].get("crop_status") == "harvestable"
                      and l.get("owner_data", {}).get("player_id") != config.PLAYER_ID]
            result.stealable = len(steals)
            for l in steals[:config.MAX_STEAL]:
                ok, gained = steal_from_land(l["land_id"], l["crop"]["crop_id"])
                if ok:
                    result.stolen += 1
                    result.stolen_grain += gained
                time.sleep(0.5)
    result.grain, result.stone = get_currency()
    return result

def check_status():
    result = FarmResult()
    gt = get("/api/common/time")
    if gt: result.game_time = gt.get("string", "?")
    result.grain, result.stone = get_currency()
    _scan_lands(result)
    _scan_seeds(result)
    chunk = get(f"/api/map/{config.MAP_ID}/land/chunk?x=70&y=0&w=30&h=30")
    if chunk:
        steals = [l for l in chunk if l.get("crop") and l["crop"].get("crop_status") == "harvestable"
                  and l.get("owner_data", {}).get("player_id") != config.PLAYER_ID]
        result.stealable = len(steals)
    return result
