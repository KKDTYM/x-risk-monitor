---
name: x-account-risk
description: 抓取 X(Twitter) 账号公开推文并通过 11 维度风险引擎(风险分逻辑，分数越高风险越大)评分，生成可视化 HTML 报告。当用户要求"评估某 X 账号风险""给 @handle 打分""分析 X 账号合规性""生成 X 账号风险评估报告"，或需要绕过 X 自动化限流抓取真实推文 DOM 时使用。
---

# X 账号抓取 + 风险评分 Skill v5.3

一键完成：**抓真实推文（登录态 DOM）→ 合并转帖分类 → 11 维度风险引擎 → 可视化 HTML 报告**。
评分逻辑：**风险分**，分数越高风险越大。引擎 level：≥60 高风险 / 30–59 中风险 / <30 低风险；
监控口径：**≥46 该动手 / 34–45 该整改 / <34 常规关注**。

## v5.3 校准（2026-08-11，7 个真实死亡样本：conny_vv / ultimatesexy15 / shichengjiangya / jiajia2475 / gg64958 / mirahangzhou / jingjing0324）

1. **性服务明示 +5/个 上限 10**（可约/接线下/全国可飞/可线下/🉑线下/可以约会/可1可0/有🚪/🚪+数字/卖淫），
   **商业变现 +3/个 上限 6**（口令/课表/门槛/🛰/微信/支付宝/红包/定制/1v1/私聊/加好友等）。
2. **新增简介形态信号**：个人数据模板（身高/体重/脚码/三围/足模/写真模特）+4；跨平台引流（dy同名/抖音同名）+2；
   卖货免责声明（感谢X平台/遵守X平台规则）+2；简介综合变现（卖货词 ≥3）+3；明确“无推广/不卖图”则豁免。
3. **新号卖货人设组合**：注册 <90 天 + 卖货人设 → +5；日均涨粉 >10 → +3（封号潮高危组合）。
4. **真人感维度**：简介卖货词 ≥1 +3 / ≥3 +5；简介性服务明示 +4；单向关注营销号 +4；大V卖货号 +3；低内容高粉 +3。
5. **露骨卖货号不享受 marking 擦边折算**；认证卖货号不享受蓝标信任加分。
6. **校准结果**：5 个有推文数据的死亡样本 v5.3 评分全部 ≥46；profile-only 样本低置信度提示“需补抓推文”。

## 评分引擎表（11 维度，总分 147 → 有效维度 125 → 归一化 0-100）

| 序号 | 维度名称 | 原始分值 | 含义 |
|------|----------|---------|------|
| 1 | **ACC 计划合规** | 0-15 | 主时间线成人/敏感占比 >90% +15、>50% +12、>20% +10、≤20% 计 0。 |
| 2 | **ACC 三级标记合规** | 0-15 | 成人关键词 + 媒体 + 未标记 Sensitive Media，每条 +3（上限 15）。 |
| 3 | **API 自动回复合规** | 0-12 | API v2 2026 限制：自动回复必须提及/引用原作者（未提及 +3/次）；同一推文被回复 >10 次 +2/条；回复内容重复 >5 条 +3。 |
| 4 | **IP/网络环境合规** | 0-10 | 数据中心 IP（AWS/阿里云/腾讯云/Tor）+5；频繁 IP 切换（>5 个/周）+3；住宅 IP 正常。 |
| 5 | **Shadowban 隐形限制** | 0-10 | 搜索用户名无推文显示 +6；回复深度 <3 层 +3；印响数骤降 >50% +3；特定搜索无该账号推文 +4（需实测，注意查看者敏感过滤对照组）。 |
| 6 | **关注/粉丝比与增长** | 0-8 | 关注/粉丝比 >10:1 +4；粉丝/推文比 >50（推文 <200）+3；新号快速涨粉（<90 天 >500 粉 +3，<30 天 >200 粉 +4）。 |
| 7 | **Premium 会员等级** | 0-8 | 蓝标 -2 信任加分（认证卖货号 +0）；粉丝 >10K 未开通 +2。 |
| 8 | **内容多样性与活跃度** | 0-12 | 单一 NSFW 占比 >80% +5；原创/搬运比 <1:3 +4；60% 推文在 2 小时内 +3；>70% 互动低（<5 赞，仅 ≥5000 粉）+3；低内容高粉（推文 <30 且粉丝 >500）+3。 |
| 9 | **禁止内容零接触** | 0-25 | Tier 1（非合意/未成年/性暴力/血腥，需语境判定）1 条 +20、≥2 条 +25；Tier 2 边界 1-2 条 +5、≥3 条 +10。 |
| 10 | **账号存续风险** | 0-18 | 封禁/重生史 +4/个（上限 8）；性服务明示 +5/个（上限 10）；商业变现 +3/个（上限 6）；简介数据模板/引流/免责声明/新号卖货组合另计；开盒 +5；幼态 +4。 |
| 11 | **真人感/营销号形态** | 0-14 | 简介卖货词 ≥1 +3 / ≥3 +5；简介性服务明示 +4；单向关注营销号 +4；大V卖货 +3；低内容高粉 +3；卖货占比 ≥50% +6；生活化 <8% +3；转帖 >50% +3；生活化 ≥50% 减免 -4。 |

等级：引擎 ≥60 = 高风险（红）；30-59 = 中风险（黄）；<30 = 低风险（绿）。
监控口径：≥46 该动手 / 34-45 该整改 / <34 常规关注。
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
- 输出：`data/<handle>_risk.json`（score/level/dimensions 11 维度/meta/tweets）。

### Step 3 生成 HTML 报告

```bash
python scripts/gen_report.py <workspace>/data/<handle>_risk_v3.json [output.html]
```

- v5 十一维度报告：总分圆环 + 11 维度卡片（扣分标准/你的情况/改进建议）+ 关键发现（数据驱动）+ 推文样本表 + 数据覆盖说明。

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
