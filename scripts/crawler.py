#!/usr/bin/env python3
"""
good-life-time crawler — fully self-sourced data
APIs used:
  1. FamilyMart products   — foodsafety.family.com.tw (public)
  2. 7-11 products        — www.7-11.com.tw/freshfoods/ (public)
  3. PCSC eMap stores     — emap.pcsc.com.tw (public, 7-11 + 全家)
"""

import requests
import xml.etree.ElementTree as ET
import json, time, sys, re, urllib.parse
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=+8))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9",
}

OUTPUT = {"updated_at": "", "stores": []}
STORE_OUTPUT = {"updated_at": "", "stores": []}


# ─── Helpers ────────────────────────────────────────────────────────────────

def safe_int(v, default=0):
    try: return int(float(v))
    except: return default


# ─── FamilyMart Products ─────────────────────────────────────────────────────

def fetch_family_products():
    url = "https://foodsafety.family.com.tw/Web_FFD_2022/ws/QueryFsProductListByFilter"
    resp = requests.post(url, json={"MEMBER": "N", "KEYWORD": "", "INCLUDE_CLB": "N"},
                        headers={**HEADERS, "Content-Type": "application/json",
                                 "Referer": "https://foodsafety.family.com.tw/"},
                        timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("RESULT_CODE") != "00":
        print(f"[全家] error: {data.get('RESULT_DESC')}", file=sys.stderr)
        return []

    products = []
    for cat in data.get("LIST", []):
        cat_name = cat.get("CATEGORY_NAME", "")
        for item in cat.get("ITEM", []):
            pic = item.get("PROD_PIC", "")
            products.append({
                "id": f"family-{item.get('CMNO', '')}",
                "name": item.get("PRODNAME", ""),
                "original_price": 0, "friendly_price": 0, "discount_percent": 0,
                "image_url": f"https://foodsafety.family.com.tw/product_img/{pic}" if pic else "",
                "stock": "", "category": cat_name,
                "store_name": "全家便利商店", "address": "",
                "note": item.get("NOTE", "")
            })
    print(f"[全家] {len(products)} products")
    return products


# ─── 7-11 Products ─────────────────────────────────────────────────────────────

def fetch_seven_products():
    all_items = []
    for idx in range(25):
        try:
            resp = requests.get(
                f"https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx?index={idx}",
                headers={**HEADERS, "Referer": "https://www.7-11.com.tw/freshfoods/"},
                timeout=10)
            if resp.status_code != 200 or len(resp.text) < 50:
                continue
            root = ET.fromstring(resp.content)
            for item in root.findall(".//Item"):
                name = item.findtext("name", "")
                price_text = item.findtext("price", "0")
                price = safe_int(price_text)
                img = item.findtext("image", "")
                all_items.append({
                    "id": f"seven-{idx}-{len(all_items)}",
                    "name": name,
                    "original_price": price,
                    "friendly_price": price // 2 if price else 0,
                    "discount_percent": 50 if price else 0,
                    "image_url": f"https://www.7-11.com.tw/freshfoods/{img}" if img else "",
                    "stock": "", "category": f"category_{idx}",
                    "store_name": "7-11", "address": "",
                    "note": f"{item.findtext('kcal', '')} {item.findtext('content', '')}".strip()
                })
        except ET.ParseError:
            continue
        except Exception as e:
            print(f"  7-11 idx {idx} error: {e}", file=sys.stderr)
    print(f"[7-11] {len(all_items)} products")
    return all_items


# ─── PCSC eMap Stores ───────────────────────────────────────────────────────

def fetch_pcsc_stores():
    """
    PCSC eMap API — public, no auth beyond session cookie.
    Returns (seven_stores, family_stores).
    Key: must POST with URL-encoded string data, NOT dict.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Step 1: establish session (gets fwchk + ASP.NET_SessionId)
    session.get('https://emap.pcsc.com.tw/', timeout=10)

    # Step 2: fetch areacode.js for city list
    r = session.get('https://emap.pcsc.com.tw/lib/areacode.js', timeout=10)
    cities = []
    for line in r.text.split('\n'):
        if 'AreaNode' in line and 'new bu' in line:
            m = re.search(r"new AreaNode\(['\"]([^'\"]+)['\"]", line)
            m2 = re.search(r"['\"]([0-9]{2})['\"]\s*\)", line)
            if m and m2:
                cities.append((m.group(1), m2.group(1)))
    print(f"[PCSC] {len(cities)} cities")
    if not cities:
        return [], []

    seven_raw, family_raw = [], []

    for city_name, city_code in cities:
        try:
            # Get town list for this city
            encoded_city = urllib.parse.quote(city_name)
            r = session.post(
                'https://emap.pcsc.com.tw/EMapSDK.aspx',
                data=f'commandid=GetTown&cityid={city_code}&leftMenuChecked=',
                headers={'Content-Type': 'application/x-www-form-urlencoded',
                         'Referer': 'https://emap.pcsc.com.tw/emap.aspx'},
                timeout=15
            )
            towns = [t.split('</TownName>')[0].strip()
                      for t in r.content.decode('utf-8').split('<TownName>')[1:]
                      if t.split('</TownName>')[0].strip()]
        except Exception as e:
            print(f"  GetTown error for {city_name}: {e}", file=sys.stderr)
            continue

        for town in towns[:10]:  # cap 10 towns per city
            try:
                encoded_city = urllib.parse.quote(city_name)
                encoded_town = urllib.parse.quote(town)
                r = session.post(
                    'https://emap.pcsc.com.tw/EMapSDK.aspx',
                    data=f'commandid=SearchStore&city={city_name}&town={town}',
                    headers={'Content-Type': 'application/x-www-form-urlencoded',
                             'Referer': 'https://emap.pcsc.com.tw/emap.aspx'},
                    timeout=15
                )
                if len(r.text) < 100:
                    continue

                root = ET.fromstring(r.content)
                for poi in root.findall('.//GeoPosition'):
                    try:
                        def ex(tag):
                            el = poi.find(tag)
                            return el.text.strip() if el is not None and el.text else ""

                        lat_str = ex("Y"); lng_str = ex("X")
                        lat = round(float(lat_str) / 1000000, 6) if lat_str else 0.0
                        lng = round(float(lng_str) / 1000000, 6) if lng_str else 0.0
                        kind = ex("POIClass")

                        store = {
                            "id": ex("POIID").strip(),
                            "name": ex("POIName").strip(),
                            "tel": ex("Telno").strip(),
                            "addr": ex("Address").strip(),
                            "lat": lat, "lng": lng,
                        }

                        if "7-11" in kind or "統一" in kind:
                            seven_raw.append(store)
                        elif "全家" in kind or "Family" in kind or "萊爾富" in kind:
                            family_raw.append(store)
                    except Exception:
                        continue
            except Exception as e:
                continue

            time.sleep(0.3)

    # Deduplicate
    seen_seven = set()
    seven_deduped = [s for s in seven_raw if s["id"] not in seen_seven and not seen_seven.add(s["id"])]
    seen_family = set()
    family_deduped = [s for s in family_raw if s["id"] not in seen_family and not seen_family.add(s["id"])]

    print(f"[PCSC] 7-11: {len(seven_deduped)}, 全家: {len(family_deduped)}")
    return seven_deduped, family_deduped


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    OUTPUT["updated_at"] = datetime.now(TZ).isoformat()
    STORE_OUTPUT["updated_at"] = OUTPUT["updated_at"]

    family_products = fetch_family_products()
    time.sleep(1)
    seven_products = fetch_seven_products()
    time.sleep(1)
    seven_stores, family_stores = fetch_pcsc_stores()

    OUTPUT["stores"] = [
        {"id": "family", "name": "全家", "name_en": "FamilyMart", "color": "#3B82F6",
         "products": family_products},
        {"id": "seven", "name": "7-11", "name_en": "Seven-Eleven", "color": "#F97316",
         "products": seven_products},
    ]
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(OUTPUT, f, ensure_ascii=False, indent=2)
    print(f"[OK] data.json — family={len(family_products)}, seven={len(seven_products)}")

    STORE_OUTPUT["stores"] = [
        {"id": "seven", "name": "7-11", "name_en": "Seven-Eleven", "color": "#F97316",
         "stores": [{"id": s["id"], "name": s["name"], "tel": s["tel"],
                    "addr": s["addr"], "lat": s["lat"], "lng": s["lng"]}
                   for s in seven_stores]},
        {"id": "family", "name": "全家", "name_en": "FamilyMart", "color": "#3B82F6",
         "stores": [{"id": s["id"], "name": s["name"], "tel": s["tel"],
                    "addr": s["addr"], "lat": s["lat"], "lng": s["lng"]}
                   for s in family_stores]},
    ]
    with open("data/stores.json", "w", encoding="utf-8") as f:
        json.dump(STORE_OUTPUT, f, ensure_ascii=False, indent=2)
    total = sum(len(s["stores"]) for s in STORE_OUTPUT["stores"])
    print(f"[OK] stores.json — {total} total stores (seven={len(seven_stores)}, family={len(family_stores)})")


if __name__ == "__main__":
    main()