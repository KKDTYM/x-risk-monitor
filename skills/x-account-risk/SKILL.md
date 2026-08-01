---
name: x-account-risk
description: 抓取 X(Twitter) 账号公开推文并通过 9 维度风险引擎(风险分逻辑，分数越高风险越大)评分，生成可视化 HTML 报告。当用户要求"评估某 X 账号风险""给 @handle 打分""分析 X 账号合规性""生成 X 账号风险评估报告"，或需要绕过 X 自动化限流抓取真实推文 DOM 时使用。
---

# X 账号抓取 + 风险评分 Skill v4.3

一键完成：**抓真实推文（登录态 DOM）→ 合并转帖分类 → 9 维度风险引擎 → 可视化 HTML 报告**。
评分逻辑：**风险分**，分数越高风险越大（≥60 高风险 / 30–59 中风险 / <30 低风险）。

## v4.1 引擎修正（2026-08-01 实战验证，与 v4 的差异）

1. **ACC 计划合规只按成人内容占比判定**：主时间线成人/敏感占比 >20% 才 +10；漏标媒体不再“双重计分”（漏标只由维度 2 负责）。
2. **Tier 1 语境化**：`萝莉/正太/cp/强迫/强奸/下药/未成年` 等词必须与严重语境共现才算 Tier 1（如“被玩具强奸了”=角色扮演、“蛋糕别下药”=自嘲梗、“未成年女友是吧”=调侃），灰色词降级 Tier 2 并提示人工复核。
3. **低互动惩罚仅适用于 ≥5000 粉账号**：小号互动低属正常现象，避免结构性误伤。
4. **短英文关键词词边界匹配**：`ts`、`cp`、`sub`、`18+` 等不再子串误匹配。

## v4.2 新增：第 10 维度「账号存续风险」（2026-08-01）

**背景**：v4/v4.1 衡量“内容合规”，但平台封禁概率还取决于账号历史与运营模式。
实测发现大量“复活号/被冻重开号”按原模式运营（性交易广告、公开联系方式），再封概率极高，却只得低分。

**第 10 维度：账号存续风险（0-15）**
- 封禁/重生史信号（复活版/重生号/被冻/冻结/重开/復活/旧号/被盗号等，仅简介+原创内容）：+4/个，上限 +8
- 性交易/商业变现信号（接线下/可约/全国可飞/莞式/报价/课表/口令/好友位/涩涩基地/包夜/线上一对一/门槛(需带数字)/付费/有偿/包月/订阅/打赏/图包/电报/加群/淘宝/店铺/发售等）：+3/个，上限 +7；“无/不+词”的声明不扣
- 隐私泄露/开盒信号（地址是/家庭住址/住址）：+5

**误报防护**：只扫描简介 + 本账号原创/回复（转帖不算）；已排除宽泛词（新号/封号/被封/线下/约吗/援交——实测“QQ被封”与“援交”自嘲梗大量误报）；“无图包/不约炮”等否定声明不扣分；“门槛”需与数字共现（门槛300），“门槛是什么”这类提问不扣分。

## 评分引擎表（10 维度，总分 130 → 归一化 0-100）

| 序号 | 维度名称 | 原始分值 | 含义 |
|------|----------|---------|------|
| 1 | **ACC 计划合规** | 0-15 | 主时间线成人/敏感内容占比 >20% 且无 ACC 计划成员证据 +10（2026 年强制）；占比 ≤20% 计 0。 |
| 2 | **ACC 三级标记合规** | 0-15 | 成人关键词 + 媒体 + 未标记 Sensitive Media，每条 +3（上限 15）。 |
| 3 | **API 自动回复合规** | 0-12 | API v2 2026 限制：自动回复必须提及/引用原作者（未提及 +3/次）；同一推文被回复 >10 次 +2/条；回复内容重复 >5 条 +3。 |
| 4 | **IP/网络环境合规** | 0-10 | 数据中心 IP（AWS/阿里云/腾讯云/Tor）+5；频繁 IP 切换（>5 个/周）+3；住宅 IP 正常。 |
| 5 | **Shadowban 隐形限制** | 0-10 | 搜索用户名无推文显示 +6；回复深度 <3 层 +3；印响数骤降 >50% +3；特定搜索无该账号推文 +4（需实测，注意查看者敏感过滤对照组）。 |
| 6 | **关注/粉丝比与增长** | 0-8 | 关注/粉丝比 >10:1 +4；粉丝机器人占比 >30% +3；关注列表 >50% 被封 +2。 |
| 7 | **Premium 会员等级** | 0-8 | Premium Basic 0；Premium -2 信任加分；Premium+ -5；粉丝 >10K 未开通 +2（蓝标推断 Premium）。 |
| 8 | **内容多样性与活跃度** | 0-12 | 单一 NSFW 占比 >80% +5；原创/搬运比 <1:3 +4；60% 推文在 2 小时内 +3；>70% 互动低（<5 赞，仅 ≥5000 粉） +3。 |
| 9 | **禁止内容零接触** | 0-25 | Tier 1（非合意/未成年/性暴力/血腥，需语境判定）1 条 +20、≥2 条 +25；Tier 2 边界 1-2 条 +5、≥3 条 +10。 |
| 10 | **账号存续风险** | 0-15 | 封禁/重生史 +4/个（上限 8）；性交易/招嫖信号 +3/个（上限 7）；隐私泄露/开盒 +5。 |

等级：总分 ≥60 = 高风险（红）；30-59 = 中风险（黄）；<30 = 低风险（绿）。
详细实现见随包 `risk_engine.py` 的 `_get_dimensions_v4()`。

## 前置依赖

- **Node + Playwright**：`npm i playwright`；支持 `channel: 'msedge'/'chrome'`（用系统浏览器可免 `npx playwright install chromium`）。
- **Python 3.10+**：随包 `risk_engine.py`（核心引擎，需复制到项目目录）与 `scripts/*.py`。
- **登录态 cookie JSON**（Cookie-Editor 导出格式 `[{name,value,domain,path,expirationDate,...}]`），放 `<workspace>/conny_cookies.json`；任意有效 X 登录态即可，不需要目标账号本人的 cookie。
- **fxTwitter 公开资料** `work/fx_<handle>.json`：`curl https://api.fxtwitter.com/<handle>`，用于生成 profile（粉丝/认证/加入时间）与推文总数。

## 工作流（三步走 + 搜索实测）

### Step 1 抓取 + 合并转帖分类

```bash
cd <项目目录>
node scripts/fetch_x_tweets.js <Handle> [workspace_dir] [cookie_file]
python scripts/merge_timelines.py <Handle> [workspace_dir] [fx_json]
```

- `fetch_x_tweets.js`：启动无头 Chromium/Edge + 注入 cookie → 打开 `https://x.com/<Handle>`；**自动点击“此个人资料可能包含潜在的敏感内容”警告门**（`button[data-testid="empty_state_button_text"]`）；滚动增量去重收集（连续 5-8 次无新增停止）；自动展开被折叠的敏感媒体；逐条提取 ID/时间/点赞/转帖/阅读/媒体/敏感标记。输出 `data/<handle>_deep_main.json` 与 `data/<handle>_deep_replies.json`。
- `merge_timelines.py`：**主时间线全部文章计入本账号**（作者 != handle 即本账号的转帖）；回复标签页只保留作者 == handle 的回复；去重（主时间线优先）；输出 `data/<handle>_tweets.json` + `data/<handle>_profile.json`（由 fxTwitter 资料生成）。

### Step 2 跑风险评分

```bash
cd <项目目录>   # 必须含 risk_engine.py（复制自技能包根目录）
python scripts/assess_x_account.py <Handle> [workspace_dir]
```

- 可选搜索证据：`data/<handle>_search_evidence.json`（见 Step 4），提供 `search_autocomplete_absent` / `user_search_absent` / `from_search_empty` / `from_search_works` / `impersonators` 字段。
- 输出：`data/<handle>_risk_v3.json`（score/level/dimensions 9 维度/meta/tweets）。

### Step 3 生成 HTML 报告

```bash
python scripts/gen_report.py <workspace>/data/<handle>_risk_v3.json [output.html]
```

- v4 九维度报告：总分圆环 + 9 维度卡片（扣分标准/你的情况/改进建议）+ 关键发现（数据驱动）+ 推文样本表 + 数据覆盖说明。

### Step 4 搜索可见性实测（建议，供维度 5）

```bash
node scripts/search_visibility_test.js <Handle> [workspace_dir] [cookie_file]
node scripts/auto_retest.js <Handle> [workspace_dir] [cookie_file]
```

- 自动补全：检查是否出现“前往 @handle”直达入口；用户搜索：检查精确真号是否在结果中；`from:` 搜索：有结果 = 未被推文搜索限流。
- **对照组**：`from:` 零结果可能是查看者“隐藏敏感内容”设置所致（实测所有敏感账号 from: 均为空），必须用其他账号对照，不能直接判定 shadowban。
- 结果写入 `data/<handle>_search_evidence.json` 后重跑 Step 2。

## 重要坑位（详见 references/LESSONS.md）

1. **敏感个人资料警告门**：不点击“是，查看个人资料”，`article` 为 0，抓取看似成功实则为空。
2. **转帖识别**：“已转帖”横幅不在正文 `div[lang]` 中；主时间线里作者 != 本账号 = 本账号转帖（漏识别会导致搬运号分数严重低估）。
3. **媒体检测**：不能只查 `img[data-testid="tweetPhoto"]`（头像也是 pbs.twimg.com 图片）；用 `div[data-testid="tweetPhoto"/"tweetVideo"]` + `img[src*="/media/"]`，排除 `profile_images`。
4. **互动数字解析**：X 把回复/转帖/赞/书签/阅读放在同一个 aria-label，必须按关键词分别提取，不能取第一个数字。
5. **Tier 1 语境化**：灰色词（萝莉/正太/cp/强迫/下药/未成年/强奸）在成人圈常见于角色扮演、自嘲、标签语境，直接命中会大量误报。
6. **小号公平性**：<5000 粉账号互动低属正常，低互动惩罚仅适用大号。
7. **GraphQL API 持续 401**：页面能登录 ≠ API 能调，直接走 Playwright DOM。
8. **无限滚动丢节点**：必须增量去重收集（`Map`，key=id 或 time+text），不能最后一次性提取。
9. **中文资料页**：用「关注者/正在关注」正则，否则 followers/following 解析错乱。
10. **Cookie 有效性**：过期/被吊销会触发登录墙（脚本检测后 exit 3），需重新导出。

## 注意事项

- 临时测试账号不触发邮件通知；正式监控账号 ≥60 分才发邮件（如接 QQ 邮箱 MCP，`alias_id` 传字符串、`to` 传数组）。
- 数据落盘在 `<workspace>/data/`，报告 HTML 默认输出到同目录，可指定输出路径。
- cookie 属敏感凭据：仅本地使用，不要写入报告/交付物。
