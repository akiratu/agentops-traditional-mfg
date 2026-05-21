# AgentOps 平台部署指南(on-prem)

給 **工廠 IT** 或 **平台維運工程師** 用。把這份系統部署到客戶機房,讓他們的 Agent 可以開始跑。

---

## 一、版本

本指南對應 **v0.5.x**(Developer Mode UI 完整版)。其他版本可能流程略有差異,請以對應 git tag 的本檔為準。

## 二、目標環境

| 項目 | 最低需求 | 建議 |
|---|---|---|
| OS | Linux x86_64(Ubuntu 22.04 / RHEL 9)或 macOS | Linux server |
| CPU | 4 核 | 8 核 |
| RAM | 8 GB | 16 GB |
| 硬碟 | 50 GB | 200 GB(預留 trace 資料庫成長空間) |
| 網路 | 對外可連 Gemini API(或內網部署 Ollama) | 同左 |
| Docker | 24+ | 24+ |
| Docker Compose | v2+(plugin 形式) | v2+ |
| Python | 3.11+ | 3.11.x |
| Node.js | 20 LTS | 20.x |
| pnpm | 9+ | 9.x 或 10.x |

## 三、部署架構(本地單機版)

```
┌─────────────────────────────────────────────────────┐
│  客戶機房(on-prem)                                │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ PostgreSQL│  │  Langfuse │  │   UI      │         │
│  │  :5432    │  │   :3000   │  │   :3001   │         │
│  └─────┬────┘  └─────┬─────┘  └─────┬────┘         │
│        │            │              │              │
│        └────────┬───┴──────────────┘              │
│                 │                                 │
│                 ▼                                 │
│        ┌────────────────┐                         │
│        │  FastAPI       │                         │
│        │  backend :8000 │                         │
│        └────────┬───────┘                         │
│                 │                                 │
│                 ▼                                 │
│        ┌──────────────────┐                       │
│        │  Gemini API      │  ← 外網 或 內網 Ollama │
│        │  (LLM provider)  │                       │
│        └──────────────────┘                       │
└─────────────────────────────────────────────────────┘
```

Postgres + Langfuse + Backend + UI 全部在同一台 Linux server,用 docker compose 起的。Gemini API 對外連線(或部署 Ollama 走內網)。

## 四、安裝步驟

### Step 1:取得程式包

```bash
git clone https://github.com/akiratu/agentops-traditional-mfg.git
cd agentops-traditional-mfg
git checkout v0.5.x   # 用最新 release tag
```

或從 GitHub Releases 下載 tarball:
```bash
curl -L https://github.com/akiratu/agentops-traditional-mfg/archive/refs/tags/v0.5.0.tar.gz | tar xz
cd agentops-traditional-mfg-0.5.0
```

### Step 2:設定 LLM API key

```bash
cp .env.example .env
nano .env    # 或 vim
```

填以下三項(其他項目可不改):
```
LLM_PROVIDER_NAME=google
GEMINI_API_KEY=<你的 Gemini API key>
GEMINI_MODEL=gemini-2.5-pro
```

**取得 Gemini API key:** https://aistudio.google.com/apikey(個人測試)或 Google Cloud Console(Production)

**內網 / 離線方案:** 若客戶禁外網,改用 Ollama:
```
LLM_PROVIDER_NAME=openai_compatible
OPENAI_BASE_URL=http://<ollama-host>:11434/v1
OPENAI_API_KEY=ollama
GEMINI_MODEL=qwen2.5:14b-instruct   # 或其他在 Ollama pull 過的 model
```

### Step 3:Postgres 加密金鑰(Langfuse 用)

Langfuse 要求一組 32-byte hex 加密金鑰。**第一次部署時產生**,之後絕對不能變(否則歷史 trace 無法解密):
```bash
openssl rand -hex 32
```

開 `docker-compose.yml`,找到 `langfuse:` 服務的 `ENCRYPTION_KEY:` 行,把產生的字串貼上去取代預設值。

(v0.6 會把這個 key 從 docker-compose.yml 抽出來放 .env,讓部署更乾淨。)

### Step 4:啟動基礎設施(Postgres + Langfuse)

```bash
docker compose up -d postgres langfuse-db langfuse
```

等 30-60 秒,確認 healthy:
```bash
docker compose ps
# 應該看到 postgres / langfuse-db / langfuse 都是 "Up (healthy)"
```

打開 http://localhost:3000(Langfuse Web UI)— 預設帳密 `dev@agentops.local` / `dev_password`,**Production 一定要改**。

### Step 5:Python 環境 + 資料庫遷移

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "packages/agentops_core[dev]"
pip install -e "packages/flows2agents"
pip install -e "packages/showcase_agents"
alembic upgrade head
```

確認 7 個 table 都建好:
```bash
docker exec agentops-postgres psql -U agentops -d agentops -c '\dt'
# 應該看到 factory, agent, skill, anomaly_signal, rca_finding, regression_run, sop_source, alembic_version
```

### Step 6:啟動 Backend

```bash
# 開發測試
uvicorn agentops_core.main:app --host 0.0.0.0 --port 8000

# 或 systemd / supervisor / pm2(Production)— 範例見「六、Production 加固」段落
```

確認:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
curl http://localhost:8000/docs   # FastAPI 自動文件
```

### Step 7:啟動 UI

```bash
cd ui
cp .env.local.example .env.local
nano .env.local
# 改 NEXT_PUBLIC_BACKEND_URL=http://localhost:8000(本機)或對應的 server IP
pnpm install
pnpm build           # Production
pnpm start           # Production,跑 build 後的版本

# 或 dev 模式測試
pnpm dev
```

開瀏覽器 http://localhost:3001,應該看到 Sidebar + 「載入中...」(因為 DB 空的)。

### Step 8:第一次資料填入

```bash
cd ..   # 回 repo root
python scripts/seed_three_domains_for_ui.py
```

打開 UI,看到 3 個 factory + 3 個 agent + 3 個 skill + 3 個 finding。

---

## 五、設定 Langfuse trace 上傳

Backend 預設會把 LLM 呼叫的 trace 上傳到本機 Langfuse(`LANGFUSE_HOST=http://localhost:3000`)。第一次啟動需要在 Langfuse Web UI 建立 Project + 取得 API key:

1. 打開 http://localhost:3000 登入(`dev@agentops.local` / `dev_password`)
2. 進去 default org 的 Factory RCA project
3. Settings → API Keys → Create new
4. 把 Public + Secret key 填到 `.env`:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-xxx
   LANGFUSE_SECRET_KEY=sk-lf-xxx
   ```
5. 重啟 backend(讓新 env 生效)

之後所有 LLM 呼叫的 trace 都會自動上傳。

---

## 六、Production 加固

### Backend 跑 systemd

`/etc/systemd/system/agentops-backend.service`:
```ini
[Unit]
Description=AgentOps backend
After=docker.service

[Service]
WorkingDirectory=/opt/agentops-traditional-mfg
EnvironmentFile=/opt/agentops-traditional-mfg/.env
ExecStart=/opt/agentops-traditional-mfg/.venv/bin/uvicorn agentops_core.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
User=agentops

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now agentops-backend
```

### UI 跑 systemd

`/etc/systemd/system/agentops-ui.service`:
```ini
[Unit]
Description=AgentOps UI
After=agentops-backend.service

[Service]
WorkingDirectory=/opt/agentops-traditional-mfg/ui
Environment=NODE_ENV=production
ExecStart=/usr/bin/pnpm start
Restart=always
User=agentops

[Install]
WantedBy=multi-user.target
```

### TLS / 反向代理(nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name agentops.yourcompany.com;
    ssl_certificate /etc/letsencrypt/live/agentops.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/agentops.yourcompany.com/privkey.pem;

    # UI
    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    # Backend(UI 已透過 next.config.mjs rewrite /api/* 過去,所以這段可選)
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
    }
}
```

### Auth(v0.5 沒做,自己加 nginx basic auth 擋一下)

```nginx
location / {
    auth_basic "AgentOps Internal";
    auth_basic_user_file /etc/nginx/htpasswd;
    proxy_pass http://localhost:3001;
}
```

```bash
sudo htpasswd -c /etc/nginx/htpasswd admin   # 之後加帳號去掉 -c
```

v0.6 會加正式 SSO,在那之前就用 basic auth 擋著。

### 備份

每天備份 Postgres:
```bash
# crontab -e
0 2 * * * docker exec agentops-postgres pg_dump -U agentops agentops | gzip > /backup/agentops-$(date +\%Y\%m\%d).sql.gz
0 2 * * * docker exec agentops-langfuse-db pg_dump -U langfuse langfuse | gzip > /backup/langfuse-$(date +\%Y\%m\%d).sql.gz
```

保留 30 天:
```bash
find /backup -name "*.sql.gz" -mtime +30 -delete
```

### 監控

最低限度:
```bash
# 加到 cron 每 5 分鐘檢查 backend 健康
*/5 * * * * curl -sf http://localhost:8000/health || curl -X POST <你的 Slack webhook> -d '{"text":"AgentOps backend down"}'
```

進階建議:
- Prometheus / Grafana 跑 backend + Langfuse 的 metrics
- Sentry / 自家 log aggregator 接 backend 的 log

---

## 七、升級流程

```bash
cd /opt/agentops-traditional-mfg
git fetch --tags
git checkout v0.6.0       # 新版本

# Backend 升級
source .venv/bin/activate
pip install -e "packages/agentops_core[dev]" --upgrade
alembic upgrade head      # ⚠️ 重要 — 跑新 migration
sudo systemctl restart agentops-backend

# UI 升級
cd ui
pnpm install
pnpm build
sudo systemctl restart agentops-ui
```

**升級前一定要備份**(看上面備份段落)。

---

## 八、常見問題

### Q: Backend 啟動就掛
```bash
journalctl -u agentops-backend -n 50
```
最常見原因:
- `.env` 沒設好(LLM_PROVIDER_NAME / GEMINI_API_KEY)
- Postgres 沒起來(`docker compose ps` 看狀態)
- Alembic migration 沒跑(`alembic upgrade head`)

### Q: UI 打開白屏
```bash
journalctl -u agentops-ui -n 50
# 或瀏覽器 F12 開 console 看 errors
```
最常見原因:
- `NEXT_PUBLIC_BACKEND_URL` 在 `.env.local` 填錯(不能用 localhost 如果 UI 跑在不同機器)
- Backend 死掉(`curl http://localhost:8000/health` 確認)

### Q: 按下 Accept,Self-Evolve 沒跑出 v2
```bash
journalctl -u agentops-backend -n 100 | grep -i "self-evolve\|gemini\|traceback"
```
最常見原因:
- Gemini API key 過期 / 額度用完
- Network 不通(連不到 generativelanguage.googleapis.com)
- 換成 Ollama 後 model 沒 pull(`ollama pull qwen2.5:14b-instruct`)

### Q: Langfuse trace 沒上去
```bash
journalctl -u agentops-backend -n 100 | grep -i langfuse
```
最常見原因:
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` 沒設(Step 5 那段)
- Langfuse server 沒起來

### Q: 資料庫太大,怎麼清?
```sql
-- 連進 Postgres
docker exec -it agentops-postgres psql -U agentops -d agentops

-- 看大小
SELECT pg_size_pretty(pg_database_size('agentops'));

-- 清掉 6 個月前的 regression run / signal / finding(保留 factory/agent/skill)
DELETE FROM regression_run WHERE created_at < NOW() - INTERVAL '6 months';
DELETE FROM rca_finding WHERE created_at < NOW() - INTERVAL '6 months';
DELETE FROM anomaly_signal WHERE created_at < NOW() - INTERVAL '6 months';
```

---

## 九、政府計畫驗收 checklist

| 項目 | 對應段落 |
|---|---|
| ☐ 可在客戶機房 on-prem 部署(不依賴外部 SaaS) | 三、四 |
| ☐ LLM provider 可換(Gemini / Ollama / 自有) | Step 2 |
| ☐ Trace 完整保留(Langfuse) | Step 7 + 五 |
| ☐ 跑得起 metal mfg / semi / customer service 3 場域 demo | Step 8 |
| ☐ 升級流程有文件 | 七 |
| ☐ 備份流程有文件 | 六 |
| ☐ 監控建議 | 六 |
| ☐ 常見問題 troubleshooting | 八 |
| ☐ 系統可演化(Self-Evolve loop 跑得通) | 完整 demo 可驗證 |

---

## 十、聯絡

平台問題 / bug:GitHub Issues https://github.com/akiratu/agentops-traditional-mfg/issues
demo / 計畫進度:akiratu(專案負責人)
