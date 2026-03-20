<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Playwright-Chromium-brightgreen?logo=playwright" />
  <img src="https://img.shields.io/badge/GPT--4o-OpenAI-412991?logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-Dashboard-black?logo=flask" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

<h1 align="center">LinkedinTouch</h1>
<p align="center">LinkedIn cold outreach automation — scrape, generate, send, repeat.</p>

---

<p align="center">
  <a href="#english">English</a> ·
  <a href="#繁體中文">繁體中文</a>
</p>

---

<a name="english"></a>

## English

### What is LinkedinTouch?

LinkedinTouch is a LinkedIn cold outreach automation tool. It scrapes prospect profiles matching your target job titles and industry keywords, generates personalized messages with GPT-4o, and sends them via Playwright browser automation.

A web dashboard lets you run everything from the browser — no terminal required.

> **Current campaign:** ChainThink — user growth solutions and media advertising for crypto / Web3 projects.

---

### Features

| Feature | Description |
|---------|-------------|
| **Cartesian Search** | Combines job titles × industry keywords (e.g. `"CMO crypto"`, `"Growth Manager Web3"`) for precise LinkedIn filtering without unreliable industry facets |
| **AI Campaign Builder** | Describe your target audience in plain text; GPT-4o auto-fills job titles and industry keywords |
| **Scrape** | Searches LinkedIn People Search and saves prospects to SQLite |
| **Generate** | GPT-4o writes a personalized ≤300-char message per prospect (auto-detects TW/HK → Traditional Chinese) |
| **Send** | Playwright sends connection requests with a note, or direct messages |
| **Dry-run** | Full simulation — browser opens but nothing is submitted |
| **Mock messages** | Test the entire pipeline without calling OpenAI |
| **Web Dashboard** | Live stats, prospect list with filters, one-click controls, inline terminal output |
| **Status management** | Manually mark any prospect as Messaged / Skipped / Failed / New from the dashboard |
| **Campaign Config UI** | Edit job titles and industry keywords directly in the browser; changes persist across runs |
| **Daily caps** | Configurable scrape and send limits; auto-stops when reached |
| **Error screenshots** | Auto-captures screenshots on send failures into `logs/errors/` |

---

### Tech Stack

| Layer | Technology |
|-------|------------|
| Browser automation | Playwright (Chromium) |
| Message generation | OpenAI GPT-4o |
| Database | SQLite (built-in `sqlite3`) |
| Web dashboard | Flask + vanilla JS |
| CLI | Click |
| Terminal output | Rich |

---

### Project Structure

```
LinkedinTouch/
├── main.py               # CLI entry point (scrape / generate / send / status / login)
├── config.py             # Campaign settings, daily caps, file paths
├── utils.py              # Logging setup, screenshot helper
│
├── auth/
│   ├── login.py          # Playwright LinkedIn login → saves session cookies
│   └── session.py        # Restores session into browser context
│
├── scraper/
│   ├── search.py         # Builds Cartesian keyword queries, paginates search results
│   ├── profile.py        # Scrapes individual profile pages
│   └── rate_limiter.py   # Daily cap enforcement + human-like delays
│
├── generator/
│   ├── generate.py       # OpenAI API call with retry logic
│   └── prompt.py         # System prompt (ChainThink pitch) + user prompt builder
│
├── outreach/
│   ├── dispatcher.py     # Routes each prospect to DM or connection-request flow
│   ├── send.py           # Sends LinkedIn direct message
│   └── connect.py        # Sends connection request with personalized note
│
├── db/
│   ├── schema.py         # SQLite schema initialization
│   └── repo.py           # Prospect & message CRUD, stats queries
│
├── web/
│   ├── app.py            # Flask API (data, run jobs, status patch, campaign CRUD, AI suggest)
│   └── templates/
│       └── index.html    # Dashboard UI
│
├── tests/
│   ├── test_generate.py  # Message generation unit tests
│   └── test_outreach.py  # Dispatcher / send / connect unit tests (mocked Playwright)
│
├── requirements.txt
└── .env.example
```

---

### Installation

#### 1. Clone and install dependencies

```bash
git clone https://github.com/andrewchang0910/LinkedinTouch.git
cd LinkedinTouch

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux / WSL
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

#### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
OPENAI_API_KEY=sk-your_openai_key
```

#### 3. Set your campaign target

Open `config.py` and edit the `CAMPAIGN` block — or use the **Campaign Config** panel in the web dashboard (no file editing needed).

```python
CAMPAIGN = {
    "job_titles": [
        "CMO", "Head of Growth", "Growth Manager", "Marketing Director", ...
    ],
    "industry_keywords": [          # Combined with job_titles for Cartesian search
        "crypto", "blockchain", "Web3", "DeFi", "NFT",
    ],
    "company_sizes": ["B", "C", "D", "E"],  # B=1-10, C=11-50, D=51-200, E=201-500
}

DAILY_SCRAPE_CAP  = 40
DAILY_MESSAGE_CAP = 20
```

---

### Usage

#### First-time login (once only)

```bash
python main.py login
```

A browser window opens — complete the LinkedIn login (including 2FA if enabled). Session is saved to `session.json` automatically.

#### CLI commands

```bash
# Scrape up to 30 prospects
python main.py scrape --limit 30

# Generate personalized messages with GPT-4o
python main.py generate

# Generate sample messages without calling OpenAI (for testing)
python main.py generate --mock

# Simulate sending (browser opens, nothing is submitted)
python main.py send --dry-run

# Send messages
python main.py send

# View campaign stats
python main.py status
```

---

### Web Dashboard

Start the Flask server:

```bash
python -m flask --app web/app.py run --port 5000
```

Open [http://localhost:5000](http://localhost:5000)

#### Dashboard panels

| Panel | Description |
|-------|-------------|
| **Controls** | Run Scrape / Generate / Send with one click; output streams to inline terminal |
| **Campaign Config** | Edit job titles and industry keywords in the browser; **AI Create** button fills them from a plain-text description |
| **Stats cards** | Total / Messaged / Pending / Failed / Skipped |
| **Daily progress bars** | Today's scrape and send counts vs. daily caps |
| **Prospect list** | Filter by status; click any row to expand full message, LinkedIn link, and status controls |
| **Status controls** | Mark any prospect as Messaged / Skipped / Reset to New / Failed without touching the CLI |

#### AI Campaign Builder

1. Open the **Campaign Config** panel
2. Type your target audience, e.g. `"crypto and Web3 project marketing and growth people"`
3. Click **✦ AI Create** — GPT-4o returns a structured list of job titles and industry keywords
4. Review, then click **Save Campaign** — changes apply to the next scrape

---

### Running Tests

```bash
pytest tests/ -v
```

All tests mock OpenAI and Playwright — no account or browser required.

---

### Data Files

| File | Description |
|------|-------------|
| `linkedintouch.db` | SQLite database (all prospects and messages) |
| `session.json` | LinkedIn session cookies — **never commit to Git** |
| `campaign.json` | Runtime campaign overrides saved by the dashboard — gitignored |
| `logs/activity.log` | Full activity log |
| `logs/errors/` | Auto-screenshots on send failures |

---

### Deduplication

- Each LinkedIn profile URL is stored once (database UNIQUE constraint)
- Prospects with a pending or sent message are skipped by the generate step
- Messaged prospects are never re-selected

---

### Safety Notes

- `.env` and `session.json` are in `.gitignore` — they will never be committed
- Keep `DAILY_MESSAGE_CAP ≤ 20` to avoid LinkedIn rate-limiting your account
- Always test with `--mock` + `--dry-run` before your first real send

---

### FAQ

**Q: Prompted to verify again after login?**
Re-run `python main.py login`.

**Q: "Connect" button not found?**
LinkedIn occasionally changes its UI. Check the auto-screenshot in `logs/errors/` and update the selector in `outreach/connect.py`.

**Q: Message over 300 characters?**
The program hard-truncates to 300 chars (LinkedIn connection note limit). The AI prompt also enforces this.

**Q: UnicodeEncodeError on Windows?**
Make sure you're on the latest code — the cp950 special-character issue has been fixed.

---

<a name="繁體中文"></a>

---

## 繁體中文

### LinkedinTouch 是什麼？

LinkedinTouch 是一套 LinkedIn 冷開發自動化工具。根據你設定的職稱與產業關鍵字搜尋潛在客戶，用 GPT-4o 生成個人化訊息，再透過 Playwright 瀏覽器自動化發送。

Web Dashboard 讓你直接在瀏覽器操作所有流程，不需開終端機。

> **目前活動：** ChainThink — 專為加密貨幣 / Web3 專案提供用戶增長與媒體廣告投放服務。

---

### 功能一覽

| 功能 | 說明 |
|------|------|
| **笛卡爾積搜尋** | 職稱 × 產業關鍵字組合（如 `"CMO crypto"`、`"Growth Manager Web3"`），不依賴不可靠的 LinkedIn industry facet |
| **AI 活動建立器** | 用自然語言描述目標客群，GPT-4o 自動填入職稱與產業關鍵字 |
| **Scrape** | 搜尋 LinkedIn 人才頁面，將潛在客戶存入 SQLite |
| **Generate** | GPT-4o 為每位客戶生成 ≤300 字個人化訊息（自動判斷台灣/香港 → 繁中） |
| **Send** | Playwright 發送含說明的連結邀請，或直接私訊 |
| **Dry-run** | 完整模擬，開瀏覽器但不點送出 |
| **Mock 訊息** | 不呼叫 OpenAI，用內建範例測試整體流程 |
| **Web Dashboard** | 即時統計、潛在客戶列表、一鍵觸發所有步驟，輸出直接顯示在頁面 |
| **手動改狀態** | 在 Dashboard 直接將潛在客戶標記為已傳訊 / 略過 / 失敗 / 重置 |
| **前端活動設定** | 在瀏覽器編輯職稱與產業關鍵字，儲存後下次 scrape 立即生效 |
| **每日上限** | 可設定每日爬取與發送上限，超過自動停止 |
| **錯誤截圖** | 發送失敗時自動截圖存入 `logs/errors/`，方便 debug |

---

### Tech Stack

| 層級 | 技術 |
|------|------|
| 瀏覽器自動化 | Playwright (Chromium) |
| 訊息生成 | OpenAI GPT-4o |
| 資料庫 | SQLite（內建 `sqlite3`） |
| Web Dashboard | Flask + 原生 JS |
| CLI | Click |
| 終端機輸出 | Rich |

---

### 專案結構

```
LinkedinTouch/
├── main.py               # CLI 入口（scrape / generate / send / status / login）
├── config.py             # 活動設定、每日上限、路徑；自動讀取 campaign.json 覆蓋值
├── utils.py              # Logging 設定、截圖 helper
│
├── auth/
│   ├── login.py          # Playwright LinkedIn 登入，儲存 session cookie
│   └── session.py        # 載入 session 到瀏覽器 context
│
├── scraper/
│   ├── search.py         # 建立笛卡爾積 keyword 查詢，分頁收集個人資料 URL
│   ├── profile.py        # 爬取個人資料頁面
│   └── rate_limiter.py   # 每日上限控制、仿真人延遲
│
├── generator/
│   ├── generate.py       # 呼叫 OpenAI API（含 retry 邏輯）
│   └── prompt.py         # System prompt（ChainThink 推廣情境）+ user prompt 建構器
│
├── outreach/
│   ├── dispatcher.py     # 判斷走私訊或連結邀請流程；記錄結果
│   ├── send.py           # 發送 LinkedIn 私訊
│   └── connect.py        # 發送含個人化說明的連結邀請
│
├── db/
│   ├── schema.py         # SQLite schema 初始化
│   └── repo.py           # 潛在客戶與訊息的 CRUD、統計查詢
│
├── web/
│   ├── app.py            # Flask API（資料、執行任務、狀態更新、活動 CRUD、AI 建議）
│   └── templates/
│       └── index.html    # Dashboard UI
│
├── tests/
│   ├── test_generate.py  # 訊息生成 Unit Tests
│   └── test_outreach.py  # Dispatcher、send、connect Unit Tests（mock Playwright）
│
├── requirements.txt
└── .env.example
```

---

### 安裝步驟

#### 1. Clone 並安裝套件

```bash
git clone https://github.com/andrewchang0910/LinkedinTouch.git
cd LinkedinTouch

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux / WSL
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

#### 2. 設定帳號與 API Key

```bash
cp .env.example .env
```

開啟 `.env` 填入：

```env
LINKEDIN_EMAIL=你的LinkedIn信箱
LINKEDIN_PASSWORD=你的LinkedIn密碼
OPENAI_API_KEY=sk-你的OpenAI金鑰
```

#### 3. 設定活動目標

開啟 `config.py` 修改 `CAMPAIGN` 區塊，或直接使用 Web Dashboard 的 **Campaign Config** 面板（不需改程式碼）。

```python
CAMPAIGN = {
    "job_titles": [
        "CMO", "Head of Growth", "Growth Manager", "Marketing Director", ...
    ],
    "industry_keywords": [          # 與 job_titles 做笛卡爾積搜尋
        "crypto", "blockchain", "Web3", "DeFi", "NFT",
    ],
    "company_sizes": ["B", "C", "D", "E"],  # B=1-10人, C=11-50人, D=51-200人, E=201-500人
}

DAILY_SCRAPE_CAP  = 40   # 每日爬取上限
DAILY_MESSAGE_CAP = 20   # 每日發送上限
```

---

### 使用方式

#### 第一次登入（只需做一次）

```bash
python main.py login
```

瀏覽器視窗開啟後完成 LinkedIn 登入（含雙重驗證）。`session.json` 自動儲存，之後不需重複登入。

#### CLI 指令

```bash
# 爬取最多 30 個潛在客戶
python main.py scrape --limit 30

# 用 GPT-4o 生成個人化訊息
python main.py generate

# 用內建範例訊息（不呼叫 OpenAI，適合測試）
python main.py generate --mock

# 模擬發送（開瀏覽器但不點送出）
python main.py send --dry-run

# 正式發送
python main.py send

# 查看活動統計
python main.py status
```

---

### Web Dashboard

啟動 Flask 伺服器：

```bash
python -m flask --app web/app.py run --port 5000
```

開啟瀏覽器前往 [http://localhost:5000](http://localhost:5000)

#### Dashboard 功能

| 區塊 | 說明 |
|------|------|
| **Controls 面板** | 點按鈕執行 Scrape / Generate / Send，輸出即時顯示在頁面內嵌終端機 |
| **Campaign Config** | 在瀏覽器直接編輯職稱與產業關鍵字；**AI Create** 按鈕用自然語言描述自動填入 |
| **統計卡片** | 總數 / 已發送 / 待處理 / 失敗 / 略過 |
| **每日進度條** | 今日爬取與發送數量 vs 每日上限 |
| **潛在客戶列表** | 可依狀態篩選；點擊任一列展開完整訊息、LinkedIn 連結與狀態操作按鈕 |
| **手動改狀態** | 已傳訊 / 略過 / 重置為 New / 失敗，不需進 CLI |

#### AI 活動建立器使用流程

1. 展開 **Campaign Config** 面板
2. 在輸入框輸入目標描述，例如：`加密貨幣與 Web3 專案的行銷與增長人員`
3. 點 **✦ AI Create** — GPT-4o 自動填入職稱與產業關鍵字
4. 確認內容後點 **Save Campaign**，下次 scrape 即套用新設定

---

### 執行測試

```bash
pytest tests/ -v
```

測試完全 mock OpenAI 與 Playwright，不需要帳號或開啟瀏覽器即可執行。

---

### 資料存放位置

| 檔案 | 說明 |
|------|------|
| `linkedintouch.db` | SQLite 資料庫（所有潛在客戶與訊息） |
| `session.json` | LinkedIn Session Cookie — **勿上傳 Git** |
| `campaign.json` | Dashboard 儲存的活動覆蓋值 — 已加入 `.gitignore` |
| `logs/activity.log` | 所有操作紀錄 |
| `logs/errors/` | 發送失敗截圖，方便 debug |

---

### 防重複機制

- 同一個 LinkedIn URL 只存一筆（資料庫 UNIQUE 約束）
- 已有 pending / sent 訊息的潛在客戶不會重複生成
- 已發送（messaged）的潛在客戶不會再被選取

---

### 安全注意事項

- `.env` 與 `session.json` 已加入 `.gitignore`，不會上傳至 Git
- 建議 `DAILY_MESSAGE_CAP ≤ 20`，避免帳號被 LinkedIn 限制
- 第一次使用建議先搭配 `--mock` + `--dry-run` 確認流程正常

---

### 常見問題

**Q：登入後又被要求驗證怎麼辦？**
重新執行 `python main.py login` 即可。

**Q：找不到 Connect 按鈕怎麼辦？**
程式會自動截圖存到 `logs/errors/`，開圖確認 LinkedIn 頁面結構後調整 `outreach/connect.py` 的 selector。

**Q：訊息超過 300 字元怎麼辦？**
程式會自動截斷到 300 字元（LinkedIn 連結邀請說明上限），AI prompt 也有強制要求。

**Q：Windows 出現 UnicodeEncodeError？**
確認使用最新版程式碼，cp950 不支援的特殊字元問題已修正。

---

## License

MIT
