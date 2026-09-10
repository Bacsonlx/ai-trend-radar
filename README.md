# 📡 AI 趋势雷达 (AI Trend Radar)

> 每日定时聚合 `hype.replicate.dev` 的硬核工程信号（GitHub 飙升库、HuggingFace 新上架、Replicate 热门调用、Reddit 开发者讨论），利用 **Google Gemini Flash** 进行痛点提炼与智能分类，并通过 **GitHub Actions** 全自动零成本推送到 **飞书群机器人**。

---

## 🌟 核心特性

- **直击真实工程信号**：告别社交媒体营销水军与推文搬运，基于真实 Star 增速、权重下载与推理调用量发现真黑马。
- **Gemini Flash 智能研判**：自动将项目归类为【Agent & 自动化流】、【模型 & 推理革命】、【开发者神器 & 效率】、【前沿黑客 & 逆向】，并一句话说明痛点与适合人群。
- **高颜值飞书交互卡片**：定制排版，包含分类徽章、指标热度、评级星级与一键直达原始链接。
- **智能历史去重**：自动记录已推送项目，智能标记「🆕 新上榜」与「🔥 持续霸榜」，防止信息疲劳。
- **100% 零成本托管**：基于 GitHub Actions 调度，每天台北时间 09:00 定时汇总过去 24 小时的 AI 趋势，无需购买云服务器。

---

## 🚀 快速上手与部署步骤

### 第一步：获取必要密钥

1. **获取 Gemini API Key**：
   - 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)。
   - 点击 **Create API Key**，复制生成的密钥（免费额度每日完全够用）。

2. **获取飞书自定义机器人 Webhook**：
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

# 3. 编辑 .env 填入你的 GEMINI_API_KEY 与 FEISHU_WEBHOOK_URL
# （如果暂时不填 Webhook，程序会自动在控制台输出卡片预览）

# 4. 立即运行测试
python main.py
```

---

### 第三步：推送到 GitHub 启用全自动托管

1. **新建 GitHub 仓库**：
   在 GitHub 上新建一个私有或公开仓库（如 `ai-trend-radar`）。

2. **推送代码**：
   ```bash
   cd ai-trend-radar
   git init
   git add .
   git commit -m "feat: initial ai trend radar setup"
   git branch -M main
   git remote add origin git@github.com:<你的用户名>/ai-trend-radar.git
   git push -u origin main
   ```

3. **配置 GitHub Secrets**：
   - 打开 GitHub 仓库页面，点击 **Settings** ➔ **Secrets and variables** ➔ **Actions**。
   - 点击 **New repository secret**，依次添加以下环境变量：
     - `GEMINI_API_KEY`: 你的 Google AI Studio 密钥（必填）。
     - `FEISHU_WEBHOOK_URL`: 你的飞书机器人 Webhook 地址（必填）。
     - `FEISHU_SECRET`: 飞书机器人的签名密钥（可选，未开启校验则不填）。
     - `GEMINI_MODEL`: `gemini-2.5-flash`（可选，默认即为 Flash）。

4. **开启 Actions 提交权限（重要）**：
   - 在仓库的 **Settings** ➔ **Actions** ➔ **General** 页面最底部；
   - 找到 **Workflow permissions**，选择 **Read and write permissions** 并点击 Save（允许机器人持久化保存去重缓存文件 `history.json`）。

---

### 第四步：立即触发测试

- 进入 GitHub 仓库的 **Actions** 标签页。
- 在左侧选择 **Daily AI Trend Radar** 工作流。
- 点击右侧的 **Run workflow** 按钮，即可在 1 分钟内看到运行结果，并直接在飞书群中收到交互式卡片！

---

## 🛠️ 项目目录结构

```text
ai-trend-radar/
├── .github/
│   └── workflows/
│       └── daily_radar.yml    # 每天台北时间 09:00 定时执行任务
├── src/
│   ├── __init__.py
│   ├── fetcher.py            # 抓取 hype.replicate.dev 过去 24h 榜单
│   ├── deduplicator.py       # 历史记录比对与智能去重
│   ├── analyzer.py           # Gemini Flash 痛点智能提炼引擎
│   └── feishu.py             # 飞书交互式卡片构建与安全发送
├── data/
│   └── history.json          # 历史推送缓存（自动维护）
├── tests/
│   └── test_main.py          # 报告日期与时区测试
├── .env.example              # 环境变量配置模板
├── .gitignore
├── requirements.txt          # 极简依赖库 (httpx, bs4, dotenv)
├── main.py                   # 完整流水线入口
└── README.md
```
