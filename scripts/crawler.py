#!/usr/bin/env python3
"""
good-life-time crawler
Fetches:
  1. FamilyMart stores + products
  2. 7-11 stores
  3. PXMart stores (placeholder)
"""

import requests
import json
import time
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=+8))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

OUTPUT = {
    "updated_at": "",
    "stores": []
}

# ─── FamilyMart Products ──────────────────────────────────────────────────────

def fetch_family_products():
    url = "https://foodsafety.family.com.tw/Web_FFD_2022/ws/QueryFsProductListByFilter"
    payload = {"MEMBER": "N", "KEYWORD": "", "INCLUDE_CLB": "N"}
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("RESULT_CODE") != "00":
        print(f"[全家] API error: {data.get('RESULT_DESC', 'unknown')}", file=sys.stderr)
        return []

    products = []
    for cat in data.get("LIST", []):
        cat_name = cat.get("CATEGORY_NAME", "")
        for item in cat.get("ITEM", []):
            pic = item.get("PROD_PIC", "")
            img_url = f"https://foodsafety.family.com.tw/product_img/{pic}" if pic else ""
            products.append({
                "id": f"family-{item.get('CMNO', '')}",
                "name": item.get("PRODNAME", ""),
                "original_price": 0,
                "friendly_price": 0,
                "discount_percent": 0,
                "image_url": img_url,
                "stock": "",
                "category": cat_name,
                "store_name": "全家便利商店",
                "address": "",
                "note": item.get("NOTE", "")
            })

    print(f"[全家] {len(products)} products")
    return products

# ─── FamilyMart Stores ─────────────────────────────────────────────────────────

def fetch_family_stores():
    url = "https://raw.githubusercontent.com/Alan-Cheng/Friendly-Cat/main/docs/assets/family_mart_stores.json"
    resp = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    stores = resp.json()
    print(f"[全家] {len(stores)} stores")
    return stores

# ─── 7-11 Stores ──────────────────────────────────────────────────────────────

def fetch_seven_stores():
    url = "https://alan-cheng.github.io/Friendly-Cat/assets/seven_eleven_stores.json"
    resp = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    stores = resp.json()
    print(f"[7-11] {len(stores)} stores")
    return stores

# ─── Main ─────────────────────────────────────────────────────────────────────

def build_output():
    OUTPUT["updated_at"] = datetime.now(TZ).isoformat()

    # FamilyMart
    family_products = fetch_family_products()
    family_stores = fetch_family_stores()
    time.sleep(1)

    # 7-11
    seven_stores = fetch_seven_stores()

    # Output store list for selector
    store_data = {
        "updated_at": OUTPUT["updated_at"],
        "stores": [
            {
                "id": "family",
                "name": "全家",
                "name_en": "FamilyMart",
                "color": "#3B82F6",
                "stores": [
                    { "id": s["pkeynew"], "name": s["Name"], "tel": s["Tel"],
                      "addr": s["addr"], "lat": s["px_wgs84"], "lng": s["py_wgs84"] }
                    for s in family_stores
                ]
            },
            {
                "id": "seven",
                "name": "7-11",
                "name_en": "Seven-Eleven",
                "color": "#F97316",
                "stores": [
                    { "id": s["serial"], "name": s["name"], "tel": s["phone"],
                      "addr": s["addr"], "lat": s["lat"], "lng": s["lng"] }
                    for s in seven_stores
                ]
            }
        ]
    }

    with open("data/stores.json", "w", encoding="utf-8") as f:
        json.dump(store_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] stores.json saved ({len(family_stores)+len(seven_stores)} total stores)")

    # Output products
    OUTPUT["stores"].append({
        "id": "family",
        "name": "全家",
        "name_en": "FamilyMart",
        "color": "#3B82F6",
        "products": family_products
    })
    OUTPUT["stores"].append({
        "id": "seven",
        "name": "7-11",
        "name_en": "Seven-Eleven",
        "color": "#F97316",
        "products": []
    })

    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(OUTPUT, f, ensure_ascii=False, indent=2)

    total = sum(len(s["products"]) for s in OUTPUT["stores"])
    print(f"[OK] data.json saved ({total} products)")

if __name__ == "__main__":
    build_output()