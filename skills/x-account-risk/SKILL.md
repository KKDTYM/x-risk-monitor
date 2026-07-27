---
name: x-account-risk
description: 抓取 X(Twitter) 账号公开推文并通过 9 维度风险引擎(风险分逻辑，分数越高风险越大)评分，生成可视化 HTML 报告。当用户要求"评估某 X 账号风险""给 @handle 打分""分析 X 账号合规性""生成 X 账号风险评估报告"，或需要绕过 X 自动化限流抓取真实推文 DOM 时使用。
---

# X 账号抓取 + 风险评分 Skill v4

一键完成：**抓真实推文 → 跑 9 维度风险引擎 → 出可视化 HTML 报告**。
评分逻辑为「风险分」：分数越高风险越大（≥60 高风险 / 30–59 中等 / <30 低风险）。

## v4 评分引擎（9 维度，满分 150 分 → 归一化到 0-100）

v3 的 6 维度升级为 v4 的 9 维度。每个维度独立计算风险分，总分 = 各维度风险分之和，再归一化到 0-100。

| 序号 | 维度名称 | 原始分值 | 含义 |
|------|----------|---------|------|
| 1 | **ACC 计划合规** | 0-15 | 检测是否加入 X Adult Content Creator 计划。未加入 +10 分；加入但未完善资料 +7 分；已完善 0 分。2026 年强制要求。 |
| 2 | **ACC 三级标记合规** | 0-15 | 成人内容推文是否正确标记 Sensitive Media。每条未标记 +3 分（最多 15 分）。检测关键词：小穴、肉棒、男娘、femboy、ts、乳胶、女仆、nsfw、18+ 等 50+ 词。 |
| 3 | **API 自动回复合规** | 0-12 | API v2 2026 限制：自动回复必须提及/引用原作者。未提及/引用 +3 分/次；同一推文被回复 >10 次 +2 分/条；回复内容重复 >5 条 +3 分。 |
| 4 | **IP/网络环境合规** | 0-10 | 检测数据中心 IP（AWS/阿里云/腾讯云/Tor）+5 分；频繁 IP 切换（>5 个/周）+3 分。住宅 IP正常。 |
| 5 | **Shadowban 隐限流** | 0-10 | 搜索用户名无推文显示 +6 分；回复深度 <3 层 +3 分；印象数骤降 >50% +3 分；特定标签搜索无该账号推文 +4 分。 |
| 6 | **关注/粉丝比与增长** | 0-8 | 关注/粉丝比 >10:1 +4 分（疑似关注轰炸）；粉丝中机器人占比 >30% +3 分；关注列表含 >50% 被封账号 +2 分。 |
| 7 | **Premium 会员等级** | 0-8 | Premium Basic（$3/月）0 分；Premium（$8/月）-2 分信任加分；Premium+（$200/月）-5 分信任加分；粉丝>10K 但未开通 Premium +2 分。 |
| 8 | **内容多样性与活跃度** | 0-12 | 单一 NSFW 内容 >80% +5 分；原创与搬运比 <1:3 +4 分；60% 推文在 2 小时内发布 +3 分；>70% 推文互动低（<5 赞）+3 分。 |
| 9 | **禁止内容零触碰** | 0-25 | Tier 1 违规（非合意/未成年人/性暴力/剥削）1 条 +20 分，≥3 条 +25 分；Tier 2 边界内容（暧昧/暗示）1-2 条 +5 分，≥3 条 +10 分。 |

**评级标准**：总分 ≥60 = 高风险（红）；30-59 = 中等风险（橙）；<30 = 低风险（绿）。

详细评分规则见 `risk_engine.py` 中的 `_get_dimensions_v4()` 方法。

## 适用场景
- 评估某个 X 成人内容账号的长期存活风险
- 研究/对照打分机制（临时测试账号）
- 批量监控多个账号（定时任务 + 邮件通知）

## 前置依赖
- **Node + Playwright**（走真实浏览器 DOM，绕过 GraphQL 401 拦截）：`npm i playwright` 且已 `npx playwright install chromium`
- **Python 3.13** + 项目内 `risk_engine.py`（核心评分引擎，风险分逻辑）
- **登录态 cookie 文件**：任意有效 X 登录态的 cookies JSON（Cookie-Editor 导出格式：`[{name,value,domain,path,expirationDate,...}]`）。读公开推文只需任意一个有效登录态，不需要目标账号自己的 cookie。

## 工作流（三步走）

### Step 1 — 抓取推文 + 转贴识别

**方式A：标准 Playwright DOM 抓取**（推荐，适用于首次评估）
```bash
cd <项目目录>
node scripts/fetch_x_tweets.js <Handle> [workspace_dir] [cookie_file]
```
- 启动无头 Chromium + 注入 cookie → 打开 `https://x.com/<Handle>`
- 滚动页面**增量去重收集**推文（X 无限滚动会卸载视口外节点，必须增量收集，不能最后一次性提取）
- 自动点击「显示敏感内容」按钮展开被折叠的媒体（否则 `img` 不在 DOM，会漏判含成人媒体但未标注的推文）
- 输出：`<workspace>/data/<handle_lower>_tweets.json`（每条含 text/time/likes/retweets/hasMedia/possibly_sensitive）+ `<handle_lower>_profile.json`（name/bio/stats）

**方式B：Syndication API + Playwright 逐个检查转贴**（适用于已有 syndication 数据或需精确识别"已转帖"）
```bash
cd <项目目录>
python batch_fetch_retweets.py  # 批量处理已配置的账号
# 或
python parse_retweets_from_raw.py  # 从已有 tweets.json 的 raw 字段解析"已转帖"标记
```
- 从 `syndication_raw_<handle>.txt` 解析推文列表
- 用 Playwright 逐个访问每条推文 URL，提取"已转帖/Reposted" DOM 标记
- **输出每条推文的 `is_retweet`、`retweet_author` 字段**，供评分引擎检测

**方式C：从已有 tweets.json raw 字段解析**（最快，适用于已有原始数据）
```bash
python parse_retweets_from_raw.py
```
- X 的 DOM 抓取结果中 `raw` 字段已包含"已转帖"文字标记
- 正则匹配 `^(.+?)\s+已转帖\s+(.+?)\s+@\w+` 和 `^(.+?)\s+Reposted\s+(.+?)\s+@\w+`
- 补充 `is_retweet`、`retweet_author_name`、`retweet_type` 字段到每条推文
- ⚠️ **必须在评分前运行**，否则评分引擎无法识别转贴

### Step 2 — 跑风险评分
```bash
cd <项目目录>   # 必须含 risk_engine.py
python scripts/assess_x_account.py <Handle> [workspace_dir]
```
- 读取 tweets + profile → 适配成 `risk_engine.RiskEngine.assess_account()` 的入参
- 关键适配：含媒体的推文在 `raw` 字段追加 ` https://x.com/media_item`，供引擎判定「成人内容+媒体→需标记 Sensitive Media」
- ⚠️ **必须确保 tweets 含 `is_retweet` 字段**：否则评分引擎的维度3（行为真实性）7项转贴检测全部失效
  - 如 tweets.json 无 `is_retweet`，先运行 `parse_retweets_from_raw.py` 或 `batch_fetch_retweets.py` 补充
- 输出：`<workspace>/data/<handle_lower>_risk_v3.json`（score / level / dimensions{6维度 risk_score,max_risk,issues} / meta / tweets）

### Step 3 — 生成 HTML 报告
```bash
python scripts/gen_report.py <workspace>/data/<handle_lower>_risk_v3.json [output.html]
```
- 复用 `gen_report()`：总分圆环 + 6 维度卡片（含扣分标准与你的情况）+ 一致性校验（总分=各维度之和）
- 颜色映射（风险分逻辑）：高风险红 `#e74c3c` / 中等橙 `#f39c12` / 低绿 `#2ecc71`

## 评分引擎 6 维度（风险分 / 满分）

**优先级排序**（按被封概率从高到低）：

1. **行为真实性 15** — 含7项转贴相关检测 + 自动化工具/频率/内容重复/密集发布/时间均匀度检测
2. **内容标记合规 30** — 每条未标记成人内容推文 +3
3. **禁止内容零触碰 25** — Tier1违规 +20/条；Tier2边界 +5/条
4. **账号环境 10** — 新号(粉丝<100) +3；异常登录 +3；脏设备/共享IP +2；未绑手机 +2；Profile/Banner含NSFW关键词+媒体 +2
5. **举报历史 5** — 举报>5 +3；警告 +2；违规≥3 +5
6. **其他合规 5** — 每类违规 +1

### 维度3（行为真实性）7项转贴相关检测详情

| # | 检测项 | 扣分 | 说明 |
|---|--------|------|------|
| 信号1 | NSFW转贴占比 >50% | +3分 | 转贴中≥3条且成人内容占比>50% → 疑似NSFW搬运号 |
| 信号2 | 转贴占比 >80% | +5分 | 原创<20% → 疑似纯搬运号 |
| 信号3 | NSFW标签高度集中 | +2分 | 转贴中≥3条含#nsfw/#18+/#成人等标签 |
| 信号4 | 高转贴+低互动 | +2分 | 转贴>50%且平均点赞<5且推文≥10条 → 低质搬运 |
| 信号5 | 硬转推占比分级 | >50%+3分；>80%+5分 | 新版X"已转帖"≠原创内容 |
| 信号6 | 时间间隔均匀度 | CV<0.05 +2分 | 程序化发推/自动回复 |
| 信号7 | 自动化工具信号 | +5分/种 | 自动点赞/关注/批量操作/互赞等 |

### 补充行为检测（非转贴相关）

| 检测项 | 扣分 | 说明 |
|--------|------|------|
| 内容重复率 >30% | +8分上限 | 重复推文比例过高 |
| 24h密集发布 >50% | +5分上限 | 单日推文占比过高 |
| 发帖频率突增 >2倍 | +5分上限 | 与历史数据对比 |

### 评分逻辑要点

- **转贴≠原创**：新版X的"已转帖"标记必须被识别，不能计入原创推文
- **转贴行为模式**：高转贴占比 + 低互动 + NSFW集中 = 典型搬运号特征
- **维度满分封顶**：维度3行为真实性满分15分，各信号累加后取min(累加值, 15)

## 重要坑位（详见 references/LESSONS.md）
1. **GraphQL API 持续 401**：页面能登录 ≠ API 能调。X 对第三方登录态的 GraphQL 调用做了拦截。→ 改走 Playwright DOM 路线（真实浏览器不受限）。
2. **`queryId` 位置变了**：从 `responsive-web/client-web-*.js` 迁到 `x-web/x-web/entry-client-logged-out-*.js`，且初始 3 个 JS（vendor/main/zh）不含，要从 `main.js` 内搜 `operationName:"UserTweets"` 提取。结论：别折腾 GraphQL，直接用 DOM。
3. **中文 X 用「关注者」不用「粉丝」**：profile 解析正则必须匹配 `关注者|Followers|粉丝`，否则 `followers` 误判 0、`following` 被覆盖 → 账号环境维度虚扣分。
4. **无限滚动丢数据**：最后一次性 `querySelectorAll('article')` 只能拿到视口内节点（X 卸载机制）。→ 滚动时增量去重 `Map`，停止条件 `连续5次无新增`。
5. **敏感媒体折叠**：未点击「显示」时 `img` 不在 DOM，`hasMedia` 误判 false → 漏扣标记分。→ 提取时自动点击展开按钮。
6. **邮件发送**：QQ 邮箱 MCP 的 `alias_id` 传字符串（非对象），`to` 传数组；正文别重复粘贴导致请求超长。
7. **硬转推检测必须逐条访问**：Syndication API的`retweeted`字段表示当前用户是否转推，不是这条本身是否是转推。新版硬转推无"RT @"前缀、无`retweeted_status`嵌套字段。→ 必须Playwright逐个访问每条推文URL提取"已转帖/Reposted"DOM标记。
8. **两组Cookie轮换仍为空壳**：X对无头浏览器的SSR限制主要基于Cloudflare指纹或UA，而非Cookie。→ 放弃主页DOM抓取，改用Syndication API抓列表+Playwright逐个访问推文页面。
9. **`is_retweet` 字段缺失 = 评分引擎转贴检测全部失效**： tweets.json 只有 text/time/likes/hasMedia，没有 is_retweet → 维度3行为真实性维度得0分（误判为低风险）。→ **必须**在评分前运行 parse_retweets_from_raw.py 或 batch_fetch_retweets.py 补充 is_retweet 字段。实测 @dangao0709 从40分（无转贴）跳到55分（含转贴，+15分！）。

## 注意事项
- cookie 过期：Cookie-Editor 导出的 `expirationDate` 是 Unix 秒。本地未过期不代表服务端未吊销，抓取前应验证页面是否出现登录墙（脚本已内置检测，出现则 exit 3）。
- 临时测试账号不触发邮件通知；正式监控账号需 ≥60 分才发邮件。
- 数据落盘在 `<workspace>/data/`，报告 HTML 在项目根目录。
