# 每日 AI 新闻邮件推送

每天在你设定的时间点，自动收集**当天社区关注度最高**的 AI 新闻（用 Hacker News / Reddit / GitHub 的真实票数、星数排序，不是随便抓几个），整理成中文简报，发到你填的邮箱。英文新闻附**中文翻译版**。

- 形态：GitHub Actions 定时任务（免费、无需服务器常开）
- 语言：Python
- 热度信号：HN `score`、Reddit `score`、GitHub `stars`（客观、可量化）
- 邮件：Resend（需域名，送达稳）/ Gmail SMTP（零成本备选）
- 摘要/翻译：DeepSeek（OpenAI 兼容，可换通义/混元/OpenAI）

---

## 一、本地预览（无需任何密钥，先看看效果）

```bash
pip install -r requirements.txt
python main.py --dry-run
```

会在当前目录生成 `preview.html`（用浏览器打开即可看到邮件长什么样）。
此时没有 LLM key，新闻只有标题/原文；配置 key 后才有中文摘要与翻译。

---

## 二、部署到 GitHub Actions（每天自动发）

### 1. 推到 GitHub
```bash
git init
git add .
git commit -m "init ai-news-digest"
gh repo create ai-news-digest --private   # 或网页新建后 git push
git push -u origin main
```

### 2. 配置 Secrets（仓库 → Settings → Secrets and variables → Actions → New repository secret）
| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek 官网申请的 key（摘要/翻译用） |
| `RESEND_API_KEY` | Resend 官网申请的 key（发信用） |

> 若改用 Gmail SMTP：再配 `SMTP_USER`、`SMTP_PASS`（16 位应用专用密码），并把 `config.yaml` 里 `email.provider` 改成 `smtp`。

### 3. 收件邮箱 & 发送时间
改 `config.yaml`：
- `email.to` → 你的邮箱
- `schedule.send_hour` → 每天本地几点发（已内置 Asia/Shanghai 时区，按北京时间算）

### 4. 启用手动触发测试
GitHub 仓库 → Actions → 选 "每日 AI 新闻邮件推送" → **Run workflow**。
手动触发会**忽略时间立即发送**，用来验证配置是否正确。

---

## 三、关于域名（Resend 发信）

Resend 要求你有一个自己的域名（如 `news.yourname.com`），花 ~¥60–80/年在
Cloudflare / Namecheap 买一个，然后在 Resend 后台添加两条 DNS 记录验证（约 10 分钟）。
作用是**邮件从你自己的域名发出，送达率高、不进垃圾箱**。

- 买好后在 Resend 添加域名，拿到验证记录填到域名解析里。
- 把 `config.yaml` 的 `email.resend_from` 改成 `ai-news@你的域名`。
- 不想买域名？把 `email.provider` 改成 `smtp`，用 Gmail 应用专用密码，零成本（偶尔可能进垃圾箱）。

---

## 四、目录结构

```
ai-news-digest/
├── main.py            # 入口：定时判断 → 采集 → 排序 → 摘要 → 渲染 → 发送
├── config_loader.py   # 加载 config.yaml + 环境变量（密钥只走环境变量）
├── sources.py         # 采集层：HN / Reddit / GitHub / RSS（并行 + 单源容错）
├── ranker.py          # 热度排序 + 去重（核心差异化）
├── summarizer.py      # LLM 摘要/翻译（英文附中文翻译版，无 key 降级）
├── renderer.py        # 响应式 HTML 邮件模板
├── mailer.py          # Resend + Gmail SMTP 双后端
├── models.py          # 统一 NewsItem 结构
├── config.yaml        # 你的配置（时间点/邮箱/源开关）
├── requirements.txt
├── .env.example       # 密钥模板
└── .github/workflows/daily.yml   # 每小时巡检、到点发送的定时任务
```

---

## 五、常见问题

**Q：为什么每小时跑一次而不是只跑一次？**
GitHub Actions 的 cron 写死在 workflow 里、且有时区限制。本项目让 workflow 每小时唤醒一次，
由 `main.py` 判断"现在是不是你设定的发送时点"，这样**改时间只动 config.yaml，不用改 workflow**。

**Q：热度是怎么算的？**
不靠 AI 主观打分。HN/Reddit 的 `points`、GitHub 的 `stars` 是社区真实投票/收藏，直接排序取 Top。
RSS 没有热度信号，用"配额保底"保证每天都有中文精选。

**Q：没配 LLM key 能跑吗？**
能。会降级为只发标题/原文，流程不中断；配了 key 才有中文摘要与英文翻译。

**Q：想加新源？**
在 `config.yaml` 的 `sources.rss_cn` / `rss_en` 里加 RSS 地址即可；
想加新的 API 源，照 `sources.py` 里写一个返回 `List[NewsItem]` 的函数并注册到 `fetch_all`。
