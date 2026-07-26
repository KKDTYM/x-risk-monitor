# X 平台风险监控系统

> **为你的 X (Twitter) 账号上一道"安全锁"——专为小姐姐、TS/CD 从业者打造的合规巡检工具**

---

## 🎯 项目定位

X 平台的成人内容政策逐年收紧，封号、限流、Shadowban 无处不在。本系统帮助从业者**定期审视账号健康度**，在踩线之前及时纠偏，降低被封风险。

**适合谁？**
- 🌸 X 平台内容创作者（小姐姐、TS/CD 为主）
- 💼 依赖 X 引流的销售/经纪人
- 📊 拥有多账号矩阵的运营者

## ✨ 核心功能

### 🔍 9 维度风险评分引擎（v4）

| 维度 | 满分 | 检查什么 |
|------|------|---------|
| **ACC 计划合规** | 15 | 是否加入成人内容创作者计划，是否符合政策 |
| **ACC 三级标记合规** | 15 | 成人内容是否正确标注 Sensitive/Adult/Explicit |
| **API 自动回复合规** | 12 | 是否使用合规 API 回复，是否触发限流 |
| **IP 网络环境合规** | 10 | IP 是否干净，是否使用数据中心 IP/代理 |
| **Shadowban 隐限流** | 10 | 搜索结果是否可见，互动数据是否正常 |
| **关注/粉丝比与增长** | 8 | 账号关系是否健康，是否存在异常增长 |
| **Premium 会员等级** | 8 | 是否开通 Premium，等级是否匹配 |
| **内容多样性与活跃** | 12 | 发帖频率、原创比例、互动率是否合理 |
| **禁止内容零触碰** | 25 | 无 NSFW、无敏感词、无违规链接 |

**总分 100 分**，分数越**低**越安全：
- 🟢 **0-29 分**：低风险，账号健康
- 🟡 **30-59 分**：中风险，建议关注
- 🔴 **60+ 分**：高风险，建议立即整改

### 📊 HTML 可视化报告

一键生成彩色可视化报告，包含：
- 各维度风险进度条
- 推文样本（原创/转贴标注）
- 问题清单与整改建议

## 🚀 快速开始

### 1. 准备 cookies

从已登录的 Chrome 浏览器导出 X cookies（推荐用 Cookie-Editor 扩展），保存为 `cookies.json`：

```json
[
  {"name": "auth_token", "value": "...", ...},
  {"name": "ct0", "value": "...", ...},
  ...
]
```

> **提示**：HttpOnly cookies（`auth_token`、`ct0`）必须用扩展或 DevTools 复制，JS 无法读取。

### 2. 抓取目标账号数据

```bash
# 抓取单个账号
python scripts/fetch_tutu7gen1_sensitive.py

# 抓取多个账号（批量）
python scripts/fetch_accounts_batch.py
```

> **关键经验**：成人内容账号主页会弹出"敏感内容警告"，脚本会自动点击"是，查看个人资料"加载推文列表。

### 3. 运行风险评估

```python
from risk_engine import RiskEngine

engine = RiskEngine()
result = engine.assess_account(raw_data, historical_data)

print(f"风险分: {result['score']}")
print(f"风险等级: {result['level']}")
print(f"建议: {result['recommendation']}")
```

### 4. 生成 HTML 报告

```bash
python scripts/gen_tutu7gen1_v4_report.py
```

报告生成在 `data/` 目录，直接用浏览器打开即可查看可视化图表。

## 📁 项目结构

```
├── risk_engine.py          # v4 风险评估引擎（核心）
├── scripts/                # 脚本集
│   ├── fetch_*             # 推文抓取脚本（Playwright/API）
│   ├── gen_*report.py      # HTML 报告生成脚本
│   └── inspect_*.py        # 页面调试脚本
├── data/                   # 数据文件
│   ├── *_tweets_*.json     # 抓取到的推文数据
│   └── *_risk_v4.html      # 生成的风险评估报告
├── cookies.json            # X 平台 cookies（需自行准备）
├── .gitignore              # Git 忽略规则
└── README.md               # 本文件
```

## 🔧 技术栈

- **Python 3.10+**
- **Playwright**：无头浏览器抓取（支持 stealth 模式）
- **requests**：API 调用（GraphQL/syndication/REST）
- **SQLite**：cookies 数据库读取（Chrome profile）

## 📚 踩坑经验

### X 平台访问限制（2026-07 实测）

| 方式 | 状态 | 说明 |
|------|------|------|
| Playwright headless | ⚠️ 限流 | 需加 stealth，且成人账号需处理敏感警告 |
| GraphQL API | ⚠️ 401 | query_id 分散到页面 chunk，需动态提取 |
| syndication API | ⚠️ 404 | 部分账号可用 |
| REST user_timeline | ⚠️ 401 | Bearer token 频繁过期 |
| **Playwright + cookies + DOM** | ✅ 可行 | **唯一稳定方案** |

### 关键技巧

1. **敏感内容警告**：成人内容账号必须点击"是，查看个人资料"才能加载推文
2. **无限滚动去重**：X 会卸载视口外的 DOM 节点，必须滚动时增量收集
3. **中文"关注者"而非"粉丝"**：profile 解析正则必须含"关注者"
4. **GraphQL query_id 动态化**：页面加载后从 JS chunk 提取，硬编码已失效

## 📝 评分引擎 v4 更新日志

- **2026-07-26**：v4 发布，新增 ACC 计划、ACC 标记、API 回复、IP 网络、Shadowban、关注比、Premium 等维度，全面对齐 2026 X 平台政策
- **2026-07-26**：维度名称改为中文，报告可读性提升

## 📄 License

MIT

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

**维护者**: [kkdtym](https://github.com/kkdtym)  
**最后更新**: 2026-07-26
