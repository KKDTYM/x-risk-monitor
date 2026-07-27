# X 账号抓取 + 评分 — 踩坑经验（实测于 2026-07-25）

## 1. GraphQL API 走不通，直接上 DOM
- 现象：带 cookie 访问 `x.com/<handle>` 首页能加载（登录态有效，返回 271KB logged-in 页面），但调 GraphQL `UserTweets` 接口始终 **401 Unauthorized**。
- 根因：X 对第三方/脚本登录态的 GraphQL 调用做了拦截（页面能看 ≠ API 能调）。`X-Twitter-Active-User`、`X-Csrf-Token` 等头补齐后仍然 401。
- 结论：**放弃 GraphQL，改 Playwright 真实浏览器 DOM 提取**。已验证稳定抓到真实推文。

## 2. queryId 位置已迁移（仅供排查参考，不推荐走 GraphQL）
- 旧路径 `responsive-web/client-web-*.js` 已失效，现位于 `x-web/x-web/entry-client-logged-out-*.js`。
- 初始加载的 vendor/main/zh 三个 JS **不含** queryId；要从 `main.js` 内搜 `operationName:"UserTweets"` 提取 `queryId:"RIylB10EGWyBSs4ZXpQjCw"`。
- 即便拿到也对 API 调用无用（见第 1 条），仅记录供未来 X 前端结构变化时参考。

## 3. 中文 X 的 profile 解析坑（已导致虚扣分）
- 中文界面用「**关注者**」而非「粉丝」。`Following` 对应「正在关注」。
- 错误正则：`Followers|粉丝` → `followers` 匹配不到变成 0，`following` 被「603 关注者」覆盖成 603。
- 后果：`_account_environment_score` 里 `followers<100` 判定成立 → 账号环境维度虚扣 3 分。
- 修复正则：`关注者|Followers|粉丝`（followers）与 `正在关注|Following`（following）。

## 4. 无限滚动丢数据（关键）
- 现象：滚动后 DOM 里 `article[data-testid="tweet"]` 计数从 14 掉回 5（X 卸载视口外节点）。最后一次性 `querySelectorAll` 只能拿视口内。
- 修复：**滚动时增量去重收集**（`Map` 以 `time|text[:50]` 为 key），停止条件 `连续 5 次无新增`。
- 实测 @Maibao1998：单次提取只 5 条，增量收集拿到 **31 条**。

## 5. 敏感媒体被折叠导致漏判
- 未点击「显示敏感内容」时，被折叠推文的 `img` 不在 DOM → `hasMedia` 误判 false → 漏扣「成人内容未标记 Sensitive Media」。
- 修复：提取每条推文时，先找文字含「显示/查看/可能包含敏感」的按钮并 `.click()` 展开，再判断 `hasMedia`。

## 6. 评分引擎入参适配要点
- 含媒体的推文：在 `raw` 字段追加 ` https://x.com/media_item`，供 `_content_marking_score` 判定「成人内容+媒体 → 需标记」。
- 维度字段名是 `risk_score` / `max_risk`（风险分逻辑，分数越高风险越大），不是旧的 `score` / `max_score`。
- 颜色映射同步反转：高风险红 / 中等橙 / 低绿。

## 7. 邮件发送（QQ 邮箱 MCP）
- `alias_id` 传**字符串**（非对象）；`to` 传**数组** `[{email,name}]`。
- 正文不要重复粘贴导致请求超长（曾因此触发输出截断/异常）。
- 阈值：正式监控账号 ≥60 分才发邮件；临时测试账号不发。

## 8. Cookie 有效期
- Cookie-Editor 导出的 `expirationDate` 是 Unix 秒。本地未过期 ≠ 服务端未吊销。
- 抓取脚本内置登录墙检测：若页面出现「登录/Sign in」且 tweet 数为 0 → exit 3，需用户重新导出 cookies。
- 读公开推文只需任意一个有效登录态（可用其他账号的 cookie），不需要目标账号自己的 cookie。
