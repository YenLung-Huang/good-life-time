# good-life-time — 友善時光查詢網站

## 1. Concept & Vision

**Core idea**: 台灣首個以「生活感」為核心的友善時光查詢網站。不只是价格查詢，而是傳達一種「聰明生活、減少浪費」的態度。

**Target**: 北漂的年輕人（20-35歲），手機為主，随時隨地查詢超商即期品。

**Vibe**: 韓系簡約 — 乾淨、安靜、有質感。不嘔哭、不擁擠，每個元素都有呼吸的空間。

---

## 2. Design Language

### Aesthetic
- 韓系極簡，大量留白
- 暖色調（橙/米/綠）傳递「省錢+環保」温度
- Mobile-first，單手操作无忧

### Color Palette
```
Background:   #FDFAF6 (暖白)
Surface:      #FFFFFF
Text Primary: #1A1A1A
Text Secondary:#8A8A8A
Accent Green: #22C55E (全聯)
Accent Blue:  #3B82F6 (全家)
Accent Orange:#F97316 (7-11)
Border:       #E5E5E5
```

### Typography
- 標題: Inter (Google Fonts) — 簡潔幾何感
- 正文: Noto Sans TC — 繁體中文友善
- 數字: Tabular figures（排版對齊）

### Spatial System
- Base unit: 4px
- Padding: 16px / 24px
- Card gap: 12px
- Section gap: 32px

### Motion (Alpine + CSS)
- Page load: fade-in 300ms ease-out
- Card hover: translateY(-2px) + shadow 200ms
- Tab switch: opacity fade 150ms
- Pull-to-refresh indicator: spin animation

### Visual Assets
- Store logos: inline SVG（自繪簡化版）
- Category icons: emoji 或 Lucide icon（CDN）
- No stock photos

---

## 3. Layout & Structure

```
┌─────────────────────────┐
│  Logo  "good life time" │  ← 置中，16px padding
├─────────────────────────┤
│  last updated: 10:32   │  ← 小字，次要資訊
├─────────────────────────┤
│ [All] [7-11] [全家] [全聯] │  ← horizontal scroll tabs
├─────────────────────────┤
│                         │
│  ┌─────┐  ┌─────┐      │
│  │Card │  │Card │      │  ← 2-column grid, sticky header
│  └─────┘  └─────┘      │
│  ┌─────┐  ┌─────┐      │
│  │Card │  │Card │      │
│  └─────┘  └─────┘      │
│                         │
│  [ load more... ]       │  ← HTMX load more button
└─────────────────────────┘
```

**Responsive**:
- Mobile (< 640px): 2-column card grid
- Tablet (640-1024px): 3-column
- Desktop (> 1024px): 4-column, max-width 1200px centered

---

## 4. Features & Interactions

### Tab Filter (Alpine)
- All / 7-11 / 全家 / 全聯
- Active tab: bold + underline accent color
- Tap → instant filter, no page reload
- Scroll position maintained on re-select

### Product Card
- 圖片（懶載入）
- 商品名称（最多2行，overflow ellipsis）
- 原價 → 友善價（紅色刪除線 + 綠色大字）
- 折扣百分比 badge
- 商店icon + 名稱
- 剩餘数量（如有）

### Card Tap
- 點擊 card → modal 顯示大圖 + 完整資訊
- Modal: backdrop blur, 點外關閉
- Alpine modal 管理

### HTMX Auto-Refresh
- 每 15 分鐘自動 fetch 最新 data.json
- "上次更新: HH:MM" 即時顯示
- 手動下拉刷新（mobile swipe-down 或 button）
- Loading shimmer effect during fetch

### Search (可選 v1 先不做)
- 搜尋框：店名 / 商品關鍵字
- Debounced input → filter client-side

### Error States
- 網路錯誤: "無法更新，顯示上次資料" + 重試 button
- 空資料: "目前無友善時光商品"
- 載入中: shimmer skeleton cards

---

## 5. Component Inventory

### Header
- Logo text: "good life time" (Inter, 600 weight)
- Update time: small gray text

### Store Tabs
- Pill-style tabs, horizontal scroll
- Active: filled background (store color), white text
- Inactive: border only, gray text

### Product Card
- White background, 12px border-radius
- Box-shadow: 0 1px 3px rgba(0,0,0,0.1)
- Image: 1:1 aspect ratio, object-cover
- States: default / loading-skeleton / error-broken

### Modal
- Full-screen on mobile
- Centered on desktop (max 480px)
- Backdrop: rgba(0,0,0,0.5) + backdrop-blur
- Close button top-right

### Refresh Button
- Floating action button (bottom-right)
- Circular, store accent color
- Icon: refresh arrow
- Spinning animation during fetch

---

## 6. Technical Approach

### Architecture
```
GitHub Actions (15-min cron)
    → Python crawler → commits data.json → GitHub Pages
    → 靜態 HTML auto deploy

Client browser
    → HTMX polling every 15min
    → fetch data.json → Alpine render
```

### Tech Stack
- **HTML/CSS**: Tailwind CSS (CDN via PostCDN or jsdelivr)
- **JS Framework**: Alpine.js (CDN)
- **AJAX**: HTMX (CDN)
- **Data**: data.json committed to repo
- **Hosting**: GitHub Pages

### Data Model (data.json)
```json
{
  "updated_at": "2026-04-26T10:30:00+08:00",
  "stores": [
    {
      "id": "seven",
      "name": "7-11",
      "name_en": "Seven-Eleven",
      "color": "#F97316",
      "products": [
        {
          "id": "seven-123",
          "name": "XXX便當",
          "original_price": 100,
          "friendly_price": 50,
          "discount_percent": 50,
          "image_url": "https://...",
          "stock": "充足/少/熱門",
          "category": "便當",
          "store_name": "北車門市",
          "address": "台北市中正區..."
        }
      ]
    },
    {
      "id": "family",
      "name": "全家",
      "color": "#3B82F6",
      "products": [...]
    },
    {
      "id": "px mart",
      "name": "全聯",
      "color": "#22C55E",
      "products": [...]
    }
  ]
}
```

### Python Crawler
- 專門爬蟲腳本，每15分鐘執行
- 三個 stores 的 API/scraper
- 輸出干淨的 JSON
- GitHub Actions secrets 存储敏感設定

### File Structure
```
good-life-time/
├── .github/
│   └── workflows/
│       └── update.yml       # GitHub Actions cron job
├── src/
│   ├── index.html          # Main page
│   ├── style.css           # Custom styles (overrides Tailwind)
│   └── app.js              # Alpine components
├── data/
│   └── data.json           # Auto-generated, .gitignored
├── scripts/
│   └── crawler.py          # Python scraper
├── SPEC.md
└── README.md
```

---

## 7. Implementation Phases

### Phase 1: MVP (現在)
- [ ] 建立 repo + SPEC.md
- [ ] 建 static HTML（Tailwind + Alpine + HTMX）
- [ ] 手動建立測試 data.json
- [ ] 確認 UI/UX 正常

### Phase 2: Crawler
- [ ] Python crawler（7-11 → 全家 → 全聯）
- [ ] GitHub Actions workflow
- [ ] 確認定時更新正常

### Phase 3: Polish
- [ ] Mobile-first pixel perfect
- [ ] Loading shimmer
- [ ] Error states
- [ ] SEO meta tags