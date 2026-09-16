# 📡 AI 趋势雷达 (AI Trend Radar)

> 每日定时并发聚合 Hype（不含 GitHub 速增榜）、GitHub 高星活跃项目、AIHot、SoPilot、极客公园和 Horizon 的 AI、开源、硬件与科技热点，利用 **OpenAI `gpt-6-astra`** 做高质量筛选、分类和一句话说明；Google Gemini 仅在主模型不可用时兜底，并由本机 `launchd` 推送到 **飞书群机器人**。

---

## 🌟 核心特性

- **多源并发聚合**：Hype、GitHub 高星活跃项目、AIHot、SoPilot、极客公园与 Horizon 同时抓取；Hype 已排除 GitHub 速增项目，GitHub 来源仅保留总 Star ≥ 2000 且近 30 天活跃的 AI 项目，SoPilot 仅收录高热 AI 话题；任一来源超时或反爬失败都会被跳过，不会中断晨报。
- **双模型容错研判**：优先调用 OpenAI `gpt-6-astra`，失败后才调用 Gemini；两者都不可用时仍以本地规则生成晨报，保证推送流程不中断。
- **可配置优先级**：在 `config/sources.json` 的 `priority_weights` 调整推送顺序，默认是 AI 热点 > 开源项目 > 语音模型 > 其他模型。
- **高颜值飞书交互卡片**：定制排版，包含分类徽章、指标热度、评级星级与一键直达原始链接。
- **智能历史去重**：自动记录已推送项目，智能标记「🆕 新上榜」与「🔥 持续霸榜」，防止信息疲劳。
- **本机准点调度**：由 macOS `launchd` 在每天本地时间 09:30 执行，避开 GitHub Actions 的排队延迟。

---

## 🚀 快速上手与部署步骤

### 第一步：获取必要密钥

1. **获取 OpenAI API Key（主模型）**：
   - 在 OpenAI API 平台创建 API Key，填入 `OPENAI_API_KEY`。
   - 桌面版 Codex 的登录态不能直接供本地脚本调用，需使用独立的 OpenAI API Key。

2. **获取 Gemini API Key（兜底）**：
   - 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)。
   - 点击 **Create API Key**，复制生成的密钥；仅在 OpenAI 调用失败时使用。

3. **获取飞书自定义机器人 Webhook**：
   - 在飞书电脑端，选择任意你希望接收晨报的群组，点击群设置 ➔ **群机器人** ➔ **添加机器人** ➔ **自定义机器人**。
   - 机器人名称可填写 `AI 趋势雷达`，添加后复制获得的 **Webhook 地址**。
   - *(可选)*：如果勾选了“签名校验”，将密钥保存备用。

---

### 第二步：本地快速测试

你可以先在本地运行一次，确认抓取与解析是否正常：

```bash
cd ai-trend-radar

# 1. 安装轻量依赖
pip install -r requirements.txt

# 2. 复制配置文件
cp .env.example .env

# 3. 编辑 .env，至少填入 OPENAI_API_KEY 与 FEISHU_WEBHOOK_URL
#    GEMINI_API_KEY 用于 OpenAI 调用失败时兜底
# （如果暂时不填 Webhook，程序会自动在控制台输出卡片预览）

# 4. 立即运行测试
python main.py
```

---

### 第三步：安装 macOS 本地定时任务

以下命令会将 LaunchAgent 注册为当前用户的任务，每天本地时间 09:30 执行一次：

```bash
cp launchd/com.bacsonlx.ai-trend-radar.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bacsonlx.ai-trend-radar.plist
```

立即试跑一次：

```bash
launchctl kickstart -k gui/$(id -u)/com.bacsonlx.ai-trend-radar
tail -f logs/launchd.out.log
```

任务状态与故障日志：

```bash
launchctl print gui/$(id -u)/com.bacsonlx.ai-trend-radar
tail -f logs/launchd.err.log
```

> 本机需要在 09:30 前保持开机并已登录；关机或休眠期间不会执行。更新 plist 后先执行 `launchctl bootout gui/$(id -u)/com.bacsonlx.ai-trend-radar`，再重新 `bootstrap`。

---

## 🛠️ 项目目录结构

```text
ai-trend-radar/
├── launchd/
│   └── com.bacsonlx.ai-trend-radar.plist # 每天本地时间 09:30 的 LaunchAgent
├── scripts/
│   └── run_daily_radar.sh     # launchd 调用入口
├── src/
│   ├── __init__.py
│   ├── fetcher.py            # 并发抓取并解析各热点来源
│   ├── deduplicator.py       # 历史记录比对与智能去重
│   ├── analyzer.py           # OpenAI 主模型 / Gemini 兜底的智能提炼引擎
│   └── feishu.py             # 飞书交互式卡片构建与安全发送
├── data/
│   └── history.json          # 历史推送缓存（自动维护）
├── config/
│   └── sources.json          # 信息源开关、URL、条数与超时配置
├── tests/
│   └── test_main.py          # 报告日期与时区测试
├── .env.example              # 环境变量配置模板
├── .gitignore
├── requirements.txt          # 极简依赖库 (httpx, bs4, dotenv)
├── main.py                   # 完整流水线入口
└── README.md
```
