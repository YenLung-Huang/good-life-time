#!/usr/bin/env python3
"""
good-life-time crawler
Fetches friendly-time / discounted product data from:
  1. FamilyMart (全家)  - public API
  2. 7-11 (7-11)       - to be researched
  3. PXMart (全聯)      - to be researched
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
    "Referer": "https://foodsafety.family.com.tw/",
}

OUTPUT = {
    "updated_at": "",
    "stores": []
}

# ─── FamilyMart ────────────────────────────────────────────────────────────────

def fetch_family():
    """全家友善時光 (含 CLB / 非會員)"""
    url = "https://foodsafety.family.com.tw/Web_FFD_2022/ws/QueryFsProductListByFilter"
    payload = {"MEMBER": "N", "KEYWORD": "", "INCLUDE_CLB": "N"}
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("RESULT_CODE") != "00":
        print(f"[全家] API error: {data.get('RESULT_DESC', 'unknown')}", file=sys.stderr)
        return None

    products = []
    for cat in data.get("LIST", []):
        cat_name = cat.get("CATEGORY_NAME", "")
        for item in cat.get("ITEM", []):
            pic = item.get("PROD_PIC", "")
            img_url = f"https://foodsafety.family.com.tw/product_img/{pic}" if pic else ""
            products.append({
                "id": f"family-{item.get('CMNO', '')}",
                "name": item.get("PRODNAME", ""),
                "original_price": 0,   # 全家 API 未提供原價
                "friendly_price": 0,
                "discount_percent": 0,
                "image_url": img_url,
                "stock": "",
                "category": cat_name,
                "store_name": "全家便利商店",
                "address": "",
                "note": item.get("NOTE", "")
            })

    print(f"[全家]Fetched {len(products)} products across {len(data.get('LIST',[]))} categories")
    return products

# ─── 7-11 ─────────────────────────────────────────────────────────────────────

def fetch_seven():
    """
    7-11 友善時光 (i珍食)
    使用 openpoint.com.tw API endpoint。
    NOTE: 實際產品需要門市級 API，這裡示範用靜態 JSON fallback
          直到找到穩定的即時來源。
    """
    # 目前先嘗試抓取公開的 7-11 商品列表 JSON
    # 如果失敗則返回之前 FriendlyCat 備份資料
    try:
        url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 10:
            print(f"[7-11] Got response: {len(resp.text)} bytes (non-empty)")
        else:
            print(f"[7-11] API returned empty ({resp.status_code})")
    except Exception as e:
        print(f"[7-11] Fetch error: {e}", file=sys.stderr)

    # 回傳空，等待研究完成
    return []

# ─── PXMart ───────────────────────────────────────────────────────────────────

def fetch_pxmart():
    """
    全聯 友善時光 (牧場/鮮物)
    全聯沒有公開 API，這裡嘗試從網站挖潛在端點。
    """
    # 嘗試可能的 API endpoint
    candidates = [
        "https://www.pxmart.com.tw/api/friendly-products",
        "https://www.pxmart.com.tw/api/product/friendly",
        "https://www.pxmart.com.tw/fresh/api/friendly",
    ]
    for url in candidates:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and "json" in resp.headers.get("Content-Type",""):
                print(f"[全聯] Found API at {url}")
                return resp.json()
        except:
            pass

    print("[全聯] No public API found — placeholder data will be used")
    return []

# ─── Main ─────────────────────────────────────────────────────────────────────

def build_output():
    OUTPUT["updated_at"] = datetime.now(TZ).isoformat()

    # FamilyMart
    family_products = fetch_family()
    if family_products:
        OUTPUT["stores"].append({
            "id": "family",
            "name": "全家",
            "name_en": "FamilyMart",
            "color": "#3B82F6",
            "products": family_products
        })
    time.sleep(1)

    # 7-11
    seven_products = fetch_seven()
    if seven_products:
        OUTPUT["stores"].append({
            "id": "seven",
            "name": "7-11",
            "name_en": "Seven-Eleven",
            "color": "#F97316",
            "products": seven_products
        })
    time.sleep(1)

    # PXMart
    pxmart_products = fetch_pxmart()
    if pxmart_products:
        OUTPUT["stores"].append({
            "id": "pxmart",
            "name": "全聯",
            "name_en": "PX Mart",
            "color": "#22C55E",
            "products": pxmart_products
        })

    total = sum(len(s["products"]) for s in OUTPUT["stores"])
    print(f"\n[OK] Total products fetched: {total}")
    print(f"Updated at: {OUTPUT['updated_at']}")

if __name__ == "__main__":
    build_output()
    out_path = "data/data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(OUTPUT, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")