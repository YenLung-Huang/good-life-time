#!/usr/bin/env python3
"""
good-life-time crawler
排程（台灣時間）: 全家 05:00, 全聯 06:00, 7-11 08:00
"""

import requests, re, time, sys, json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=+8))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*", "Accept-Language": "zh-TW,zh;q=0.9",
}

def parse_price(text):
    if not text: return 0, 0
    text = str(text).strip()
    # "25-40元,依重量而訂" -> take first number
    m = re.search(r'(\d+)', text)
    price = int(m.group(1)) if m else 0
    return price, price // 2 if price else 0

# ── 1. FamilyMart Products ────────────────────────────────────────────

def fetch_family_products():
    url = "https://foodsafety.family.com.tw/Web_FFD_2022/ws/QueryFsProductListByFilter"
    resp = requests.post(url, json={"MEMBER": "N", "KEYWORD": "", "INCLUDE_CLB": "N"},
        headers={**HEADERS, "Content-Type": "application/json", "Referer": "https://foodsafety.family.com.tw/"},
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

# ── 2. 7-11 Products ───────────────────────────────────────────────────

def fetch_seven_products():
    all_items = []
    for idx in range(30):
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
                if not name: continue
                price, friendly = parse_price(item.findtext("price", ""))
                img = item.findtext("image", "")
                kcal = item.findtext("kcal", "")
                note = f"{kcal} " if kcal else ""
                all_items.append({
                    "id": f"seven-{idx}-{len(all_items)}",
                    "name": name,
                    "original_price": price,
                    "friendly_price": friendly,
                    "discount_percent": 50 if price else 0,
                    "image_url": f"https://www.7-11.com.tw/freshfoods/{img}" if img else "",
                    "stock": "", "category": f"category_{idx}",
                    "store_name": "7-11", "address": "",
                    "note": note.strip()
                })
        except ET.ParseError: continue
        except Exception as e:
            print(f"  7-11 idx {idx} error: {e}", file=sys.stderr)
    print(f"[7-11] {len(all_items)} products")
    return all_items

# ── 3. FamilyMart Stores ───────────────────────────────────────────────

def fetch_family_stores():
    url = "https://alan-cheng.github.io/Friendly-Cat/assets/family_mart_stores.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    stores = []
    for item in raw:
        try:
            lng = float(item.get("px_wgs84") or 0)
            lat = float(item.get("py_wgs84") or 0)
            if not lng or not lat: continue
            stores.append({
                "id": str(item.get("pkeynew", "")),
                "name": item.get("Name", ""),
                "tel": item.get("Tel", ""),
                "addr": item.get("addr", ""),
                "lat": round(lat, 6), "lng": round(lng, 6),
            })
        except: continue
    print(f"[全家] {len(stores)} stores")
    return stores

# ── 4. 7-11 Stores (PCSC) ──────────────────────────────────────────────

def fetch_pcsc_stores():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get('https://emap.pcsc.com.tw/', timeout=10)
    r = session.get('https://emap.pcsc.com.tw/lib/areacode.js', timeout=10)
    cities = []
    for line in r.text.split('\n'):
        if 'AreaNode' in line and 'new bu' in line:
            m = re.search(r"new AreaNode\(['\"]([^'\"]+)['\"]", line)
            m2 = re.search(r"['\"]([0-9]{2})['\"]\s*\)", line)
            if m and m2: cities.append((m.group(1), m2.group(1)))
    print(f"[PCSC] {len(cities)} cities")
    if not cities: return []

    all_stores = []
    for city_name, city_code in cities[:10]:
        try:
            r = session.post('https://emap.pcsc.com.tw/EMapSDK.aspx',
                data=f'commandid=GetTown&cityid={city_code}&leftMenuChecked=',
                headers={'Content-Type':'application/x-www-form-urlencoded','Referer':'https://emap.pcsc.com.tw/emap.aspx'},
                timeout=15)
            towns = [t.split('</TownName>')[0].strip()
                     for t in r.content.decode('utf-8').split('<TownName>')[1:]
                     if t.split('</TownName>')[0].strip()]
        except Exception as e:
            print(f"  GetTown {city_name} error: {e}", file=sys.stderr); continue

        for town in towns[:3]:
            try:
                r = session.post('https://emap.pcsc.com.tw/EMapSDK.aspx',
                    data=f'commandid=SearchStore&city={city_name}&town={town}',
                    headers={'Content-Type':'application/x-www-form-urlencoded','Referer':'https://emap.pcsc.com.tw/emap.aspx'},
                    timeout=15)
                if len(r.text) < 100: continue
                root = ET.fromstring(r.content)
                for poi in root.findall('.//GeoPosition'):
                    try:
                        lat_str = poi.find("Y").text if poi.find("Y") is not None else ""
                        lng_str = poi.find("X").text if poi.find("X") is not None else ""
                        lat = round(float(lat_str)/1000000, 6) if lat_str else 0.0
                        lng = round(float(lng_str)/1000000, 6) if lng_str else 0.0
                        all_stores.append({
                            "id": poi.find("POIID").text.strip() if poi.find("POIID") is not None else "",
                            "name": poi.find("POIName").text.strip() if poi.find("POIName") is not None else "",
                            "tel": poi.find("Telno").text.strip() if poi.find("Telno") is not None else "",
                            "addr": poi.find("Address").text.strip() if poi.find("Address") is not None else "",
                            "lat": lat, "lng": lng,
                        })
                    except: continue
            except: continue
            time.sleep(0.3)

    seen = set()
    deduped = [s for s in all_stores if s["id"] and s["id"] not in seen and not seen.add(s["id"])]
    print(f"[PCSC] {len(deduped)} 7-11 stores")
    return deduped

# ── Main ───────────────────────────────────────────────────────────────

def main():
    now = datetime.now(TZ).isoformat()

    family_products = fetch_family_products()
    time.sleep(1)
    seven_products = fetch_seven_products()
    time.sleep(1)
    family_stores = fetch_family_stores()
    time.sleep(0.5)
    seven_stores = fetch_pcsc_stores()

    # data.json
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now, "stores": [
            {"id":"family","name":"全家","name_en":"FamilyMart","color":"#3B82F6","products":family_products},
            {"id":"seven","name":"7-11","name_en":"Seven-Eleven","color":"#F97316","products":seven_products},
        ]}, f, ensure_ascii=False, indent=2)
    print(f"[OK] data.json — family={len(family_products)}, seven={len(seven_products)}")

    # stores.json
    with open("data/stores.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now, "stores": [
            {"id":"seven","name":"7-11","color":"#F97316",
             "stores":[{"id":s["id"],"name":s["name"],"tel":s["tel"],"addr":s["addr"],
                        "lat":s["lat"],"lng":s["lng"]} for s in seven_stores]},
            {"id":"family","name":"全家","color":"#3B82F6",
             "stores":[{"id":s["id"],"name":s["name"],"tel":s["tel"],"addr":s["addr"],
                        "lat":s["lat"],"lng":s["lng"]} for s in family_stores]},
        ]}, f, ensure_ascii=False, indent=2)
    total = sum(len(s["stores"]) for s in json.load(open("data/stores.json", encoding="utf-8"))["stores"])
    print(f"[OK] stores.json — {total} total stores")

if __name__ == "__main__":
    main()
