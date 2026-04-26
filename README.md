# good life time

> 台灣超商友善時光查詢 — 7-11、全家、全聯即期品特價網站

**設計目標**: 韓系簡約風格，Mobile-first，北漂年輕人的省錢生活利器。

**Live**: https://yenlung-huang.github.io/good-life-time/

## 功能

- ✅ 三家通路商品同時查詢（7-11、全家、全聯）
- ✅ 即時更新（每 15 分鐘自動抓取）
- ✅ 商店快速篩選（點選 Tab 即可切換）
- ✅ 商品卡片：原價 → 友善價一目了然
- ✅ 點擊看大圖 + 完整資訊
- ✅ 純靜態網站，Host 在 GitHub Pages

## Tech Stack

- **HTML/CSS**: Tailwind CSS (CDN)
- **JS**: Alpine.js (CDN)
- **Data**: 定期更新的 `data.json`
- **Hosting**: GitHub Pages
- **Automation**: GitHub Actions（每 15 分鐘更新）

## 本地開發

```bash
# 用 static server 開啟
python3 -m http.server 8080
# 然後打開 http://localhost:8080
```

## 資料格式

`data/data.json` 結構：

```json
{
  "updated_at": "2026-04-26T10:30:00+08:00",
  "stores": [
    {
      "id": "seven",
      "name": "7-11",
      "color": "#F97316",
      "products": [
        {
          "id": "seven-001",
          "name": "叉燒肉飯糰",
          "original_price": 55,
          "friendly_price": 27,
          "discount_percent": 51,
          "image_url": "https://...",
          "stock": "充足",
          "category": "飯糰",
          "store_name": "北車門市",
          "address": "台北市北平西路3號"
        }
      ]
    }
  ]
}
```

## License

MIT