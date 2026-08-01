#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X 账号风险评分引擎 v4.8（11 维度，风险分逻辑：分数越高风险越大）。

维度总分上限 = 142（15+15+12+10+10+8+8+12+25+15+12），归一化到 0-100。
等级：>=60 高风险（红） / 30-59 中风险（黄） / <30 低风险（绿）。
数据源：Playwright 登录态 DOM 时间线 + X syndication embed + fxTwitter。

v4.7 变更：
- 置信度机制：无数据维度不再假装安全，输出置信度与分数区间
- Tier2 数量分级：3-9 条 +10 / 10-49 条 +15 / 50+ 条 +20
- marking 平台标记率参照：平台整体标记率 <10% 时折算 50%（平台尺度）
- 变现信号权重下调（校准：存活样本中露骨变现组与无变现组存续年限无差异）
- 多语言词库（英文关键词）
"""
import re
from datetime import datetime

# 强成人词：明确性内容（用于敏感标记判定 / Tier2 / 成人占比）
STRONG_ADULT = [
    "小穴", "肉棒", "男娘", "femboy", "母狗", "唧唧", "鸡鸡", "牛牛",
    "性爱", "做爱", "自慰", "手冲", "口交", "肛交", "乳交", "足交",
    "阴蒂", "阴道", "阴茎", "龟头", "精液", "高潮", "色情", "淫荡",
    "淫乱", "骚货", "贱货", "肉便器", "母畜", "调教", "裸照", "裸体",
    "涩图", "色图", "r18", "r-18", "nsfw", "18+", "18禁", "onlyfans",
    "fansly", "制服诱惑", "内射", "无套", "群交", "援交", "约炮",
    "一夜情", "招嫖", "下海", "露出", "卖淫", "嫖",
    "sex", "nsfw", "porn", "hentai", "daddy", "kink", "bdsm", "spank",
    "selling content", "onlyfans", "fansly", "tribbing", "fisting",
]
# 软成人词：擦边/身体向（用于成人占比与上下文）
SOFT_ADULT = [
    "平胸", "女仆", "ts", "丝袜", "蕾丝", "写真", "福利", "图包",
    "胸", "奶子", "奶头", "屁股", "翘臀", "足控", "恋足", "spank",
    "dom", "sub", "私房", "包月", "订阅", "打赏", "内裤", "bra", "泳装",
]
# Tier 1 严重违规（非合意 / 未成年 / 性暴力 / 血腥剥刮）——仅保留无歧义严重词
TIER1_KEYWORDS = [
    "幼女", "幼男", "恋童", "恋童癖", "儿童色情", "炼铜",
    "迷奸", "诱奸", "非自愿", "性暴力", "人兽", "兽交", "犬交",
    "分尸", "剥皮", "血腥", "gore", "snuff", "凌迟",
]
# “未成年/未成年人”仅在性语境共现时算 Tier 1（排除调侃/日常语境误报）
TIER1_MINOR_CONTEXT = STRONG_ADULT + ["恋童", "儿童色情", "炼铜", "性", "色情", "操", "裸", "精液", "鸡巴"]
# “强奸”仅在与其他严重词共现时才算 Tier 1（排除成人角色扮演/玩具等语境）
TIER1_RAPE_CONTEXT = ["未成年", "幼女", "幼男", "恋童", "儿童色情", "炼铜", "迷奸", "诱奸", "轮奸", "下药", "迷药", "非自愿"]
TIER1_DRUG_CONTEXT = ["强奸", "迷奸", "诱奸", "轮奸", "未成年", "幼女", "恋童", "非自愿", "性暴力", "昏迷", "灌醉"]
# Tier 2 边界内容（性暗示 / 低俗羞辱 / 擦边）
TIER2_KEYWORDS = STRONG_ADULT + [
    "骚货", "贱货", "肉便器", "母畜", "淫", "荡妇", "烧鸡", "骚鸡",
    "白虎", "奶子", "奶头", "调教", "露出", "萝莉", "正太", "强奸", "强上",
    "去势", "阉割", "切蛋", "割鸡", "阉奴", "母狗", "骚逼", "鸡巴",
]

# ---- 第 10 维度：账号存续风险（封禁史与平台打击面）----
# 封禁/重生历史信号：账号曾因违规被平台处理，重启后再次违规 = 再封高优先级
SURVIVAL_BAN_KEYWORDS = [
    "复活版", "重生号", "重生", "被冻", "冻结",
    "重开", "復活", "旧号", "被盗号", "号被盗",
    # 第二轮校准（v4.8）：恢复“被封”类精确模式（避免裸词“被封”误报 QQ 封号）
    "大号被封", "老号被封", "账号被封", "号被封了", "秽土转生", "转生",
]
# 性交易/招嫖 + 商业变现信号（A 级=露骨明示，必须扣分）
SURVIVAL_SW_KEYWORDS = [
    "接线下", "可约", "全国可飞", "全国可✈", "莞式", "报价",
    "课表", "口令", "好友位", "私信解锁", "涩涩基地", "包夜", "线上一对一",
    "领课表", "接单", "约炮", "门槛", "付费", "有偿", "包月", "订阅", "打赏",
    "图包", "淘宝", "店铺", "发售", "卖淫", "下单",
]
# 隐晦引流词（B 级=可辩解，不扣分，仅提示）
SURVIVAL_IMPLICIT_KEYWORDS = [
    "电报", "tg", "加群", "可线下", "🉑线下", "私信", "找我", "加我", "解锁", "购买", "价格",
]
# 隐私侵害信号：泄露他人姓名/住址等（开盒）
SURVIVAL_DOX_KEYWORDS = ["地址是", "家庭住址", "住址"]
# 幼态/未成年误判风险：账号自述被平台识别为未成年（幼态人设+性话题=平台误杀高发区）
SURVIVAL_MINOR_MISJUDGE_KEYWORDS = [
    "识别成未成年", "识别未成年", "被识别未成年", "像未成年", "幼年时期", "幼态", "未成年警告",
]

# ---- 第 11 维度：真人感 / 营销号形态 ----
# 生活化关键词：真人博主会有日常/个人叙事
LIFE_KEYWORDS = [
    "吃饭", "午饭", "晚饭", "早餐", "天气", "下雨", "上课", "上班", "下班",
    "实习", "考试", "作业", "累了", "好累", "朋友", "室友", "爸妈", "睡觉",
    "头疼", "感冒", "生病", "vlog", "心情", "吐槽", "生日", "放假", "回家",
    "剪头发", "逛街", "喝酒", "唱歌",
]
# 卖货/引流关键词（A 级=露骨明示，计入营销号形态）
SELL_KEYWORDS = [
    "口令", "课表", "门槛", "好友位", "报价", "下单", "发售", "店铺",
    "淘宝", "有偿", "付费", "包月", "订阅", "打赏", "图包", "涩涩", "接单",
    "可约", "莞式", "私信解锁", "线上一对一", "接线下", "包夜", "约炮",
]
# 隐晦引流词（B 级=不扣分，仅提示）
SELL_IMPLICIT_KEYWORDS = [
    "电报", "tg", "加群", "私信", "找我", "加我", "解锁", "可线下", "🉑线下", "购买", "价格",
]


def _hit(text, keywords):
    low = (text or "").lower()
    for kw in keywords:
        k = kw.lower()
        if re.search(r"^[a-z0-9+]+$", k) and len(k) <= 4:
            if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", low):
                return True
        elif k in low:
            return True
    return False


def _parse_int(v):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"([\d,]+)", str(v))
    return int(m.group(1).replace(",", "")) if m else 0


class RiskEngine:
    def __init__(self, config):
        self.config = config or {}

    def assess_account(self, raw_data, extra_data=None):
        extra_data = extra_data or {}
        profile = raw_data.get("profile", {}) or {}
        dims = self._get_dimensions_v4(raw_data, extra_data)
        total = sum(d["risk_score"] for d in dims.values())
        max_total = sum(d["max_risk"] for d in dims.values())
        score = max(0, min(100, round(total / max_total * 100)))
        level = "high" if score >= 60 else "medium" if score >= 30 else "low"

        # ---- v4.7 置信度：无数据维度 + 样本覆盖率 ----
        statuses = _parse_int(profile.get("statuses", 0))
        n_tweets = len(raw_data.get("recent_tweets", []) or [])
        coverage = (n_tweets / statuses) if statuses > 0 else 1.0
        unverified = 2  # api_reply + ip_network 无数据
        if not extra_data.get("search_visibility_tested"):
            unverified += 1  # shadowban 未实测
        confidence = 100 - unverified * 6 - max(0, int((1 - coverage) * 50))
        confidence = max(30, min(95, confidence))
        score_range = [max(0, score - 10), min(100, score + 10)]

        details = []
        for key, d in dims.items():
            for issue in d.get("issues", []):
                details.append(f"[{d.get('label', key)}] {issue}")
        if not details:
            details.append("未发现明显违规信号")

        rec_map = {
            "high": "高风险：建议立即整改——下架/标注全部成人内容，加入 ACC 计划，规范资料与互动，处理举报与违规记录。",
            "medium": "中风险：建议尽快整改——确认 ACC 计划状态，规范敏感标记，注意搜索可见性与内容合规，防范仿冒诈骗。",
            "low": "低风险：当前样本未发现严重违规，但内容以成人向为主，建议确认 ACC 计划状态并防范仿冒诈骗。",
        }
        return {
            "score": score,
            "level": level,
            "confidence": confidence,
            "coverage": round(coverage, 3),
            "score_range": score_range,
            "dimensions": dims,
            "details": details,
            "recommendation": rec_map[level],
        }

    def _get_dimensions_v4(self, raw_data, extra_data):
        profile = raw_data.get("profile", {}) or {}
        tweets = raw_data.get("recent_tweets", []) or []
        followers = _parse_int(profile.get("followers_count", 0))
        following = _parse_int(profile.get("following_count", 0))

        # 主时间线推文（用于“账号发布内容”类指标）
        timeline_posts = [t for t in tweets
                          if t.get("source") in ("timeline_dom", "main")
                          or (not t.get("source") and not t.get("is_reply"))]
        if not timeline_posts:
            timeline_posts = tweets

        strong_hits, soft_hits, flagged, media_unmarked = [], [], [], []
        tier1_ids, tier2_ids = [], []
        for t in tweets:
            text = t.get("text") or t.get("raw") or ""
            strong = _hit(text, STRONG_ADULT)
            soft = _hit(text, SOFT_ADULT)
            sens = bool(t.get("possibly_sensitive")) or bool(t.get("is_sensitive"))
            if strong:
                strong_hits.append(t)
            if soft:
                soft_hits.append(t)
            if sens:
                flagged.append(t)
            if strong and (t.get("hasMedia") or t.get("media")) and not sens:
                media_unmarked.append(text[:60])
            has_minor = "未成年" in text.lower()
            is_tier1 = _hit(text, TIER1_KEYWORDS) or (
                has_minor and _hit(text, TIER1_MINOR_CONTEXT)
            ) or (
                "强奸" in text.lower() and _hit(text, TIER1_RAPE_CONTEXT)
            ) or (
                ("下药" in text.lower() or "迷药" in text.lower()) and _hit(text, TIER1_DRUG_CONTEXT)
            ) or (
                "轮奸" in text.lower() and _hit(text, TIER1_RAPE_CONTEXT)
            )
            if has_minor and not is_tier1:
                # 含“未成年”但无性语境：降级为 Tier 2 边界，报告中提示人工复核
                if not any(x is t for x in tier2_ids):
                    tier2_ids.append(t)
            if is_tier1:
                tier1_ids.append(t)
            if _hit(text, TIER2_KEYWORDS):
                if not any(x is t for x in tier2_ids):
                    tier2_ids.append(t)

        n_all = max(1, len(tweets))
        n_main = max(1, len(timeline_posts))
        nsfw_main = sum(1 for t in timeline_posts
                        if bool(t.get("possibly_sensitive")) or bool(t.get("is_sensitive"))
                        or _hit(t.get("text") or t.get("raw") or "", STRONG_ADULT + SOFT_ADULT))
        nsfw_ratio_main = nsfw_main / n_main
        tier1_count = len(tier1_ids)
        tier2_count = len(tier2_ids)

        # ---- 5 维度证据：搜索可见性实测（2026-07-31）----
        _handle = extra_data.get("handle", "该账号")
        _sb_score = 4 if (extra_data.get("search_autocomplete_absent") or extra_data.get("user_search_absent")) else 0
        _sb_issues = []
        if extra_data.get("search_autocomplete_absent") or extra_data.get("user_search_absent"):
            _sb_issues.append(f"实测：搜索“{_handle}”，自动补全与用户搜索均不出现真号 @{_handle}，仿冒/相似号占据结果（+4）")
        if extra_data.get("from_search_empty"):
            _sb_issues.append(f"from:{_handle} 无推文结果，但对照组同样为空时判定为查看者敏感内容过滤所致，不重复扣分")
        if not _sb_issues:
            _sb_issues.append("无搜索可见性异常证据")

        # ---- 10 维度证据：账号存续风险（封禁史 / 性交易信号 / 隐私侵害）----
        # 仅扫描简介 + 本账号原创/回复内容（转帖是别人的内容，不算账号自述，避免误报）
        _all_texts = [(profile.get("description") or "")]
        _all_texts += [(t.get("text") or t.get("raw") or "") for t in tweets if not t.get("is_retweet")]
        _ban_hits = []
        _sw_hits = []
        _dox_hits = []
        _impl_hits = []
        _minor_hits = []
        _impersonator_count = len(extra_data.get("impersonators") or [])
        for txt in _all_texts:
            for kw in SURVIVAL_BAN_KEYWORDS:
                if kw in txt and ("无" + kw) not in txt and ("不" + kw) not in txt and kw not in _ban_hits:
                    _ban_hits.append(kw)
            for kw in SURVIVAL_SW_KEYWORDS:
                if ("无" + kw) in txt or ("不" + kw) in txt or kw in _sw_hits:
                    continue
                if kw == "门槛" and not re.search(r"门槛\s*\d", txt):
                    # “门槛”需与数字共现（如 门槛300/🚪门槛300），单独提问不算变现
                    continue
                if kw in txt:
                    _sw_hits.append(kw)
            for kw in SURVIVAL_IMPLICIT_KEYWORDS:
                if kw in txt and not any(a in txt for a in SURVIVAL_SW_KEYWORDS) and kw not in _impl_hits:
                    _impl_hits.append(kw)
            for kw in SURVIVAL_DOX_KEYWORDS:
                if kw in txt and ("无" + kw) not in txt and ("不" + kw) not in txt and kw not in _dox_hits:
                    _dox_hits.append(kw)
            for kw in SURVIVAL_MINOR_MISJUDGE_KEYWORDS:
                if kw in txt and kw not in _minor_hits:
                    _minor_hits.append(kw)
        # 校准（v4.8）：第二轮 11 vs 149 对比推翻 v4.7 结论——
        # 重生史组 bio 露骨变现比例 55% vs 无史组 23%（+0.31），变现号更容易被封，上限恢复 7
        _survival = min(8, len(_ban_hits) * 4) + min(7, len(_sw_hits) * 3) + (5 if _dox_hits else 0)
        # 新号信号：注册 <1 年且无蓝标（重生号显著更年轻：中位 1 年 vs 4 年）
        _joined = profile.get("joined") or ""
        _joined_year = None
        _jm = re.search(r"\b(19|20)\d{2}\b", _joined)
        if _jm:
            _joined_year = int(_jm.group(0))
        _is_new = _joined_year is not None and (2026 - _joined_year) < 1
        if _is_new and not (profile.get("is_blue_verified") or profile.get("verified")):
            _survival += 2
        if _minor_hits:
            _survival += 4
        if _impersonator_count >= 6:
            _survival += 4
        elif _impersonator_count >= 3:
            _survival += 2
        _survival = min(15, _survival)
        _surv_issues = []
        if _ban_hits:
            _surv_issues.append(f"检测到封禁/重生史信号：{'、'.join(_ban_hits[:6])}（账号已被平台处理过，再封优先级高，+{min(8, len(_ban_hits) * 4)}）")
        if _sw_hits:
            _surv_issues.append(f"检测到性交易/商业变现信号：{'、'.join(_sw_hits[:8])}（平台重点打击 + 法律风险，+{min(5, len(_sw_hits) * 3)}）")
        if _impl_hits:
            _surv_issues.append(f"检测到隐晦引流词（未扣分，仅提示）：{'、'.join(_impl_hits[:6])}")
        if _dox_hits:
            _surv_issues.append(f"检测到疑似隐私泄露/开盒信号：{'、'.join(_dox_hits[:4])}（涉他人真实信息，+5）")
        if _minor_hits:
            _surv_issues.append(f"检测到幼态/未成年误判信号：{'、'.join(_minor_hits[:4])}（幼态人设+性话题=平台误杀高发区，需人工复核，+4）")
        if _impersonator_count:
            _surv_issues.append(f"发现 {_impersonator_count} 个仿冒/近似账号（{'、'.join((extra_data.get('impersonators') or [])[:6])}），仿冒生态侵蚀粉丝，+{2 if _impersonator_count >= 3 else 4 if _impersonator_count >= 6 else 0}")
        if _is_new and not (profile.get("is_blue_verified") or profile.get("verified")):
            _surv_issues.append(f"注册不足 1 年且无认证（新号，重生号显著更年轻：中位 1 年 vs 4 年，+2）")
        if not _surv_issues:
            _surv_issues.append("未检测到封禁史/性交易/隐私侵害信号")

        # ---- 11 维度证据：真人感 / 营销号形态 ----
        _own_tweets = [t for t in tweets if not t.get("is_retweet")]
        _n_own = max(1, len(_own_tweets))
        _n_all = max(1, len(tweets))
        _life_cnt = sum(1 for t in _own_tweets if _hit(t.get("text") or t.get("raw") or "", LIFE_KEYWORDS))
        _sell_cnt = sum(1 for t in _own_tweets if _hit(t.get("text") or t.get("raw") or "", SELL_KEYWORDS))
        _sell_impl_cnt = sum(1 for t in _own_tweets
                             if _hit(t.get("text") or t.get("raw") or "", SELL_IMPLICIT_KEYWORDS)
                             and not _hit(t.get("text") or t.get("raw") or "", SELL_KEYWORDS))
        _repost_cnt = sum(1 for t in tweets if t.get("is_retweet"))
        _life_ratio = _life_cnt / _n_own
        _sell_ratio = _sell_cnt / _n_own
        _repost_ratio = _repost_cnt / _n_all
        _bio_sell = sum(1 for kw in SELL_KEYWORDS if kw in (profile.get("description") or ""))
        _bio_sell_impl = sum(1 for kw in SELL_IMPLICIT_KEYWORDS
                             if kw in (profile.get("description") or "")
                             and not any(a in (profile.get("description") or "") for a in SELL_KEYWORDS))
        _human_score = 0
        _human_break = {}
        if _sell_ratio >= 0.5:
            _human_score += 6
            _human_break["卖货内容占比"] = f"{_sell_ratio*100:.0f}% 推文含卖货/引流词（>=50%，+6）"
        elif _sell_ratio >= 0.25:
            _human_score += 3
            _human_break["卖货内容占比"] = f"{_sell_ratio*100:.0f}% 推文含卖货/引流词（>=25%，+3）"
        else:
            _human_break["卖货内容占比"] = f"{_sell_ratio*100:.0f}% 推文含卖货/引流词（<25%，+0）"
        if _bio_sell >= 2:
            _human_score += 3
            _human_break["简介卖货"] = f"简介含 {_bio_sell} 个露骨卖货词（>=2，营销号形态，+3）"
        elif _bio_sell == 1:
            _human_break["简介卖货"] = f"简介含 1 个露骨卖货词（<2，+0）"
        else:
            _human_break["简介卖货"] = f"简介露骨卖货词 0 个（+0）"
        if _sell_impl_cnt or _bio_sell_impl:
            _human_break["隐晦引流提示"] = f"检测到隐晦引流词（推文 {_sell_impl_cnt} 条/简介 {_bio_sell_impl} 个），不扣分仅提示"
        if _life_ratio < 0.08:
            _human_score += 3
            _human_break["生活化内容"] = f"仅 {_life_ratio*100:.0f}% 推文有生活化内容（<8%，疑似纯营销号，+3）"
        else:
            _human_break["生活化内容"] = f"{_life_ratio*100:.0f}% 推文有生活化内容（>=8%，+0）"
        if _repost_ratio > 0.5:
            _human_score += 3
            _human_break["搬运占比"] = f"转帖占 {_repost_ratio*100:.0f}%（>50%，搬运号，+3）"
        else:
            _human_break["搬运占比"] = f"转帖占 {_repost_ratio*100:.0f}%（<=50%，+0）"
        _human_discount = 0
        if _life_ratio >= 0.5:
            _human_discount = 4
            _human_break["真人感减免"] = f"生活化内容 {_life_ratio*100:.0f}%（>=50%，真人博主形态，-4）"
        elif _life_ratio >= 0.25:
            _human_discount = 2
            _human_break["真人感减免"] = f"生活化内容 {_life_ratio*100:.0f}%（>=25%，-2）"
        else:
            _human_break["真人感减免"] = f"生活化内容 {_life_ratio*100:.0f}%（<25%，无减免）"
        _human_score = max(0, min(12, _human_score - _human_discount))

        # ---- 7 维度证据：Premium 状态 ----
        _prem_score = -2 if (profile.get("is_blue_verified") or profile.get("verified")) else (2 if followers > 10000 else 0)
        _prem_issues = ["蓝标认证 → 推断开通 Premium（-2 信任加分）"] if (profile.get("is_blue_verified") or profile.get("verified")) else (
            [f"粉丝 {followers} >10K 但未见 Premium 标记（+2）"] if followers > 10000
            else [f"粉丝 {followers} <10K，Premium 维度无加分/扣分"]
        )

        # ---- 2 维度证据：平台标记率（校准 marking 尺度）----
        _platform_mark_rate = len(flagged) / n_all
        _mark_raw = min(15, len(media_unmarked) * 3)
        _mark_score = _mark_raw
        _mark_issues = [f"{len(media_unmarked)} 条含成人关键词媒体未标记 Sensitive Media（每条 +3）"]
        if media_unmarked and _platform_mark_rate < 0.10:
            _mark_score = round(_mark_raw * 0.5)
            _mark_issues.append(f"平台整体标记率仅 {_platform_mark_rate*100:.1f}%（<10%，平台认可的擦边尺度），按 50% 折算（{_mark_raw} -> {_mark_score}）")
        elif media_unmarked:
            _mark_issues.append(f"平台整体标记率 {_platform_mark_rate*100:.1f}%（>=10%），漏标按正常规则扣分")
        else:
            _mark_issues = [f"{len(flagged)}/{len(tweets)} 条推文已被 X 标记敏感，无漏标"]

        dims = {
            # ---- 1. ACC 计划合规 (0-15) ----
            "acc_plan": {
                "label": "ACC 计划合规",
                "risk_score": 10 if nsfw_ratio_main > 0.2 else 0,
                "max_risk": 15,
                "issues": (
                    [f"主时间线 {nsfw_main}/{n_main} 条为成人/敏感内容（{nsfw_ratio_main*100:.0f}%），"
                     "未检测到 ACC 计划成员证据，按“未加入”计分（+10；若已加入可下调）"]
                    if nsfw_ratio_main > 0.2
                    else [f"主时间线成人/敏感内容占比 {nsfw_ratio_main*100:.0f}%（<=20%），非成人内容账号形态，本维度计 0 分"]
                ),
                "adult_ratio_main": round(nsfw_ratio_main, 3),
                "adult_media_unmarked": len(media_unmarked),
            },
            # ---- 2. ACC 三级标记合规 (0-15) ----
            "marking": {
                "label": "ACC 三级标记合规",
                "risk_score": _mark_score, "max_risk": 15,
                "issues": _mark_issues,
                "platform_mark_rate": round(_platform_mark_rate, 3),
                "total_adult_tweets": len(strong_hits) + len(soft_hits),
                "flagged_count": len(flagged),
                "unflagged_count": len(media_unmarked),
            },
            # ---- 3. API 自动回复合规 (0-12) ----
            "api_reply": {
                "label": "API 自动回复合规",
                "risk_score": 0, "max_risk": 12,
                "issues": ["无 API 自动回复日志（本维度计 0 分，无法验证）"],
            },
            # ---- 4. IP/网络环境合规 (0-10) ----
            "ip_network": {
                "label": "IP/网络环境合规",
                "risk_score": 0, "max_risk": 10,
                "issues": ["无 IP/网络环境数据（本维度计 0 分，无法验证）"],
            },
            # ---- 5. Shadowban 隐形限制 (0-10) ----
            "shadowban": {
                "label": "Shadowban 隐形限制",
                "risk_score": _sb_score,
                "max_risk": 10,
                "issues": _sb_issues,
            },
            # ---- 6. 关注/粉丝比与增长 (0-8) ----
            "follow_ratio": {
                "label": "关注/粉丝比与增长",
                "risk_score": 4 if (following > 0 and followers > 0 and following / followers > 10) else 0,
                "max_risk": 8,
                "issues": [f"关注/粉丝比 {following}/{followers} 正常", "粉丝机器人占比/关注列表封号率无法验证（计 0 分）"],
                "following": following,
                "followers": followers,
                "ratio": round(following / followers, 4) if followers else None,
            },
            # ---- 7. Premium 会员等级 (0-8, 可为负) ----
            "premium": {
                "label": "Premium 会员等级",
                "risk_score": _prem_score,
                "max_risk": 8,
                "issues": _prem_issues,
                "verified": bool(profile.get("is_blue_verified") or profile.get("verified")),
            },
        }

        # ---- 8. 内容多样性与活跃度 (0-12) ----
        low_likes = sum(1 for t in tweets if _parse_int(t.get("likes")) < 5)
        retweets = sum(1 for t in tweets if t.get("is_retweet"))
        original_ratio = 1 - retweets / n_all
        burst_count = self._two_hour_burst(tweets)
        d8 = 0
        d8_breakdown = {}
        if nsfw_ratio_main > 0.8:
            d8 += 5
            d8_breakdown["单一 NSFW 占比"] = f"主时间线成人/敏感内容 {nsfw_ratio_main*100:.0f}% > 80%（+5）"
        else:
            d8_breakdown["单一 NSFW 占比"] = f"主时间线成人/敏感内容 {nsfw_ratio_main*100:.0f}%（<=80%，+0）"
        if original_ratio < 0.25:
            d8 += 4
            d8_breakdown["原创/搬运比"] = f"原创仅 {original_ratio*100:.0f}% < 25%（+4）"
        else:
            d8_breakdown["原创/搬运比"] = f"原创 {original_ratio*100:.0f}%（>=25%，+0）"
        if burst_count >= 0.6 * n_all:
            d8 += 3
            d8_breakdown["集中发布"] = f"{burst_count}/{n_all} 条推文在 2 小时窗口内发布（+3）"
        else:
            d8_breakdown["集中发布"] = f"2 小时窗口内最多 {burst_count} 条（<60%，+0）"
        # 低互动惩罚仅适用于 5000 粉以上账号：小号互动低属正常现象，避免结构性误伤
        if low_likes / n_all > 0.7 and followers >= 5000:
            d8 += 3
            d8_breakdown["低互动"] = f"{low_likes}/{n_all} 条互动 <5 赞（{low_likes/n_all*100:.0f}% > 70%，粉丝 {followers} >=5000，+3）"
        elif low_likes / n_all > 0.7:
            d8_breakdown["低互动"] = f"{low_likes}/{n_all} 条互动 <5 赞（{low_likes/n_all*100:.0f}% > 70%，但粉丝 {followers} <5000，小号正常现象不扣分）"
        else:
            d8_breakdown["低互动"] = f"{low_likes}/{n_all} 条互动 <5 赞（{low_likes/n_all*100:.0f}%，<=70%，+0）"
        dims["content_diversity"] = {
            "label": "内容多样性与活跃度",
            "risk_score": min(12, d8), "max_risk": 12,
            "issues": [f"{k}：{v}" for k, v in d8_breakdown.items()],
            "deduction_breakdown": d8_breakdown,
            "low_likes_count": low_likes,
            "total_tweets": len(tweets),
        }

        # ---- 9. 禁止内容零接触 (0-25) ----
        d9 = 0
        d9_issues = []
        if tier1_count >= 2:
            d9 += 25
            d9_issues.append(f"Tier 1 严重违规 {tier1_count} 条（+25）")
        elif tier1_count == 1:
            d9 += 20
            d9_issues.append("Tier 1 严重违规 1 条（+20）")
        else:
            d9_issues.append("未检出 Tier 1（非合意/未成年/性暴力/血腥）违规")
        if 1 <= tier2_count <= 2:
            d9 += 5
            d9_issues.append(f"Tier 2 边界内容 {tier2_count} 条（1-2 条 +5）")
        elif tier2_count >= 50:
            d9 += 20
            d9_issues.append(f"Tier 2 边界内容 {tier2_count} 条（≥50 条 +20，擦边浓度极高）")
        elif tier2_count >= 10:
            d9 += 15
            d9_issues.append(f"Tier 2 边界内容 {tier2_count} 条（10-49 条 +15）")
        elif tier2_count >= 3:
            d9 += 10
            d9_issues.append(f"Tier 2 边界内容 {tier2_count} 条（3-9 条 +10）")
        else:
            d9_issues.append("未检出 Tier 2 边界内容")
        dims["prohibited"] = {
            "label": "禁止内容零接触",
            "risk_score": min(25, d9), "max_risk": 25,
            "issues": d9_issues,
            "tier1_violations": tier1_count,
            "tier1_details": [(("（搬运）" if t.get("is_retweet") else "") + (t.get("text", "")[:80])) for t in tier1_ids],
            "tier2_count": tier2_count,
            "tier2_details": [t.get("text", "")[:100] for t in tier2_ids],
        }
        dims["survival"] = {
            "label": "账号存续风险",
            "risk_score": _survival, "max_risk": 15,
            "issues": _surv_issues,
            "ban_hits": _ban_hits[:8],
            "sw_hits": _sw_hits[:10],
            "dox_hits": _dox_hits[:4],
            "minor_hits": _minor_hits[:5],
            "impersonator_count": _impersonator_count,
        }
        dims["human"] = {
            "label": "真人感/营销号形态",
            "risk_score": _human_score, "max_risk": 12,
            "issues": [f"{k}：{v}" for k, v in _human_break.items()],
            "life_ratio": round(_life_ratio, 3),
            "sell_ratio": round(_sell_ratio, 3),
            "repost_ratio": round(_repost_ratio, 3),
        }
        return dims

    @staticmethod
    def _two_hour_burst(tweets):
        times = []
        for t in tweets:
            ts = t.get("time") or ""
            if not ts:
                continue
            try:
                times.append(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
            except Exception:
                continue
        if len(times) < 3:
            return 0
        times.sort()
        best = 1
        j = 0
        for i in range(len(times)):
            while j < len(times) and times[j] - times[i] <= 7200:
                j += 1
            best = max(best, j - i)
        return best


if __name__ == "__main__":
    r = RiskEngine({}).assess_account({
        "account_status": "normal",
        "profile": {"description": "", "followers_count": 0, "following_count": 0, "is_sensitive": False},
        "recent_tweets": [],
        "is_sensitive": False,
    })
    print("self-check score:", r["score"], r["level"])
