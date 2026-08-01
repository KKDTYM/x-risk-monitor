# X 账号风险评分

> X(Twitter) 账号健康度巡检工具，9 维度风险评分，可视化 HTML 报告。

---

## 快速开始

### 1. 准备 cookie

从已登录 Chrome 导出 X cookie，保存为 `data/*.cookies.json`：

```json
[
  {"name": "auth_token", "value": "..."},
  {"name": "ct0", "value": "..."}
]
```

> HttpOnly cookies（`auth_token`、`ct0`）必须用 Cookie-Editor 扩展或 DevTools 复制。

### 2. 抓取推文 + 评分

```bash
# 抓取推文
python scripts/fetch_x_tweets.py <username> <cookie_path> <output_dir>

# 风险评分
python scripts/assess_x_account.py <username> <skill_dir>

# 生成报告
python scripts/gen_report.py <risk_json_path> <output_html>
```

### 3. 使用 risk_engine API

```python
from risk_engine import RiskEngine

engine = RiskEngine()
result = engine.assess(raw_data, historical_data)
print(f"风险分: {result['score']}")
```

---

## 9 维度评分

| 维度 | 满分 |
|------|------|
| ACC 计划合规 | 15 |
| ACC 三级标记合规 | 15 |
| API 自动回复合规 | 12 |
| IP 网络环境 | 10 |
| Shadowban 隐限流 | 10 |
| 关注/粉丝比 | 8 |
| Premium 等级 | 8 |
| 内容多样性 | 12 |
| 禁止内容零触碰 | 25 |

**0-29 低风险 / 30-59 中风险 / 60+ 高风险**

---

## 项目结构

```
├── risk_engine.py           # 评分引擎
├── scripts/                 # 脚本
│   ├── fetch_x_tweets.py    # 推文抓取
│   ├── assess_x_account.py  # 评分
│   └── gen_report.py        # HTML 报告
├── data/                    # 数据文件
└── README.md
```

## 技术栈

- Python 3.10+
- Playwright（无头浏览器）
- requests（API 调用）

## 踩坑记录

详见 `references/LESSONS.md`

---

**维护**: [kkdtym](https://github.com/kkdtym)
