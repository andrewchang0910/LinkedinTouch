# LinkedinTouch

LinkedIn 冷開發自動化工具。自動搜尋目標職稱的潛在客戶、爬取個人資料、用 GPT-4o 生成個人化訊息，並透過 Playwright 瀏覽器自動化發送連結邀請或私訊。

Web Dashboard 讓你直接在瀏覽器操作所有流程，不需開終端機。

---

## 功能一覽

| 功能 | 說明 |
|------|------|
| **Scrape** | 依職稱、產業、地區、公司規模搜尋 LinkedIn，將潛在客戶存入 SQLite |
| **Generate** | 用 GPT-4o 為每位潛在客戶生成個人化訊息（支援繁中／英文自動判斷） |
| **Send** | 透過 Playwright 發送連結邀請附加說明（≤300 字）或 LinkedIn 私訊 |
| **Dry-run** | 模擬完整發送流程，不實際點擊送出 |
| **Mock 訊息** | 不呼叫 OpenAI，用內建範例訊息測試整體流程 |
| **Web Dashboard** | 即時統計、潛在客戶列表、Controls 面板一鍵觸發任何步驟 |
| **每日上限** | 可設定每日爬取與發送上限，超過自動停止 |
| **錯誤截圖** | 發送失敗或找不到按鈕時自動截圖，存入 `logs/errors/` 方便 debug |

---

## Tech Stack

| 層級 | 技術 |
|------|------|
| 瀏覽器自動化 | Playwright (Chromium) |
| 訊息生成 | OpenAI GPT-4o |
| 資料庫 | SQLite (`sqlite3`) |
| Web Dashboard | Flask + 原生 JS |
| CLI | Click |
| 終端機輸出 | Rich |

---

## 專案結構

```
LinkedinTouch/
├── main.py               # CLI 入口（scrape / generate / send / status / login）
├── config.py             # 活動設定、每日上限、路徑
├── utils.py              # Logging 設定、截圖 helper
│
├── auth/
│   ├── login.py          # Playwright LinkedIn 登入，儲存 session cookie
│   └── session.py        # 載入 session 到瀏覽器 context
│
├── scraper/
│   ├── search.py         # 從 LinkedIn 搜尋頁收集個人資料 URL
│   ├── profile.py        # 爬取個人資料頁面
│   └── rate_limiter.py   # 每日上限控制、仿真人延遲
│
├── generator/
│   ├── generate.py       # 呼叫 OpenAI API 生成訊息
│   └── prompt.py         # System / user prompt 模板
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
│   ├── app.py            # Flask Dashboard（/api/data、/api/run、/api/job）
│   └── templates/
│       └── index.html    # Dashboard UI（統計、列表、Controls 面板）
│
├── tests/
│   ├── test_generate.py  # 訊息生成 Unit Tests
│   └── test_outreach.py  # Dispatcher、send、connect Unit Tests（mock Playwright）
│
├── requirements.txt
└── .env.example
```

---

## 安裝步驟

### 1. Clone 並安裝套件

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

### 2. 設定帳號與 API Key

```bash
cp .env.example .env
```

開啟 `.env` 填入：

```env
LINKEDIN_EMAIL=你的LinkedIn信箱
LINKEDIN_PASSWORD=你的LinkedIn密碼
OPENAI_API_KEY=sk-你的OpenAI金鑰
```

### 3. 設定活動目標

開啟 `config.py`，修改 `CAMPAIGN` 區塊：

```python
CAMPAIGN = {
    "job_titles": ["HR Manager", "Recruiter", "Talent Acquisition"],
    "industries": ["Technology", "Financial Services"],
    "regions":    ["Taiwan", "Hong Kong"],
    "company_sizes": ["C", "D", "E"],  # C=11-50人, D=51-200人, E=201-500人
}

DAILY_SCRAPE_CAP  = 40   # 每日爬取上限
DAILY_MESSAGE_CAP = 20   # 每日發送上限
```

公司規模代碼：`B`=1–10、`C`=11–50、`D`=51–200、`E`=201–500、`F`=501–1k、`G`=1k–5k

---

## 使用方式

### 第一次登入（只需做一次）

```bash
python main.py login
```

瀏覽器視窗開啟後完成 LinkedIn 登入（含雙重驗證）。登入成功後 `session.json` 自動儲存，之後不需重複登入。

---

### CLI 分步執行

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

## Web Dashboard

啟動 Flask 伺服器：

```bash
python -m flask --app web/app.py run --port 5000
```

開啟瀏覽器前往 [http://localhost:5000](http://localhost:5000)

### Dashboard 功能

| 區塊 | 說明 |
|------|------|
| **Controls 面板** | 直接在瀏覽器點按鈕執行 Scrape / Generate / Send，即時顯示終端機輸出 |
| **統計卡片** | 總數 / 已發送 / 待處理 / 失敗 / 略過 |
| **每日進度條** | 今日爬取與發送數量 vs 每日上限 |
| **潛在客戶列表** | 可依狀態篩選；點擊任一列展開完整訊息與 LinkedIn 連結 |

執行任何指令時，所有按鈕自動 disable；完成後自動重新整理統計資料。
頁面每 30 秒自動更新。

---

## 執行測試

```bash
pytest tests/ -v
```

測試完全 mock OpenAI 與 Playwright，不需要帳號或開啟瀏覽器即可執行。

---

## 資料存放位置

| 檔案 | 說明 |
|------|------|
| `linkedintouch.db` | SQLite 資料庫（所有潛在客戶與訊息） |
| `session.json` | LinkedIn 登入 Session（勿上傳 Git） |
| `logs/activity.log` | 所有操作紀錄 |
| `logs/errors/` | 發送失敗截圖，方便 debug |

---

## 防重複機制

- 同一個 LinkedIn URL 只存一筆（資料庫 UNIQUE 約束）
- 已生成訊息的潛在客戶不會重複生成
- 已發送的潛在客戶狀態改為 `messaged`，不會再被選取

---

## 安全注意事項

- `.env` 與 `session.json` 已加入 `.gitignore`，不會上傳至 Git
- 建議每日發送不超過 20 則，避免帳號被 LinkedIn 限制
- 第一次使用建議先搭配 `--dry-run` 和 `--mock` 確認流程正常

---

## 常見問題

**Q：登入後又被要求驗證怎麼辦？**
重新執行 `python main.py login` 即可。

**Q：找不到 Connect 按鈕怎麼辦？**
程式會自動截圖存到 `logs/errors/`，開圖確認 LinkedIn 頁面結構後調整 `outreach/connect.py` 的 selector。

**Q：訊息超過 300 字元怎麼辦？**
程式會自動截斷到 300 字元（LinkedIn 連結邀請說明上限）。

**Q：Windows 出現 UnicodeEncodeError？**
確認使用最新版程式碼，已修正 cp950 不支援的特殊字元問題。

---

## License

MIT
