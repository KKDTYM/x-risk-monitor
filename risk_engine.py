#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X 账号风险评分引擎 v5.4（11 维度，风险分逻辑：分数越高风险越大）。

维度总分上限 = 147（15+15+12+10+10+8+8+12+25+18+14），有效维度（不含 api_reply/ip_network）= 125，归一化到 0-100。
等级：>=60 高风险（红） / 30-59 中风险（黄） / <30 低风险（绿）。
数据源：Playwright 登录态 DOM 时间线 + X syndication embed + fxTwitter。

v4.7 变更：
- 置信度机制：无数据维度不再假装安全，输出置信度与分数区间
- Tier2 数量分级：3-9 条 +10 / 10-49 条 +15 / 50+ 条 +20
- marking 平台标记率参照：平台整体标记率 <10% 时折算 50%（平台尺度）
- 变现信号权重下调（校准：存活样本中露骨变现组与无变现组存续年限无差异）
- 多语言词库（英文关键词）

v5.0 变更（10330 样本校准，calibration_final.json）：
- 测试集 AUC 0.819（ban 特征驱动）；单特征 AUC：sell_a 0.196 / sell_b 0.253 / age 0.186 / verified 0.124——
  变现与年龄特征方向反向或随机，变现权重上限 5 -> 3（仅弱提示）
- ban（bio 封禁/重生表述）为唯一可靠信号（负样本误报极低）
- 保留：ban 上限 8、开盒 +5、幼态 +4、仿冒 +2/+4、蓝标 -2（verified 反向支持）
- 复核落盘、marking 收紧、Tier2 分级、置信度机制保持不变

v5.3 变更（7 个真实死亡样本校准：conny_vv / ultimatesexy15 / shichengjiangya / jiajia2475 /
gg64958 / mirahangzhou / jingjing0324，2026-08-10~11 封号潮）：
- 性服务明示 +5/个 上限 10（原 +4/7）；新增 可线下/🉑线下/可以约会/可1可0/有🚪/🚪+数字
- 商业变现 +3/个 上限 6（原上限 3）；新增 🛰/微信/支付宝/红包/定制/1v1/私聊/加好友
- 新增简介信号：个人数据模板（身高体重/脚码/三围/足模） +4、引流（dy同名等） +2、
  卖货免责声明（感谢X平台/遵守X平台规则） +2、简介综合变现（bio 卖货词≥3） +3
- 真人感维度：简介卖货词 ≥1 +3 / ≥3 +5；简介性服务明示 +4；单向关注营销号 +4；
  大V卖货号（>1万粉且简介卖货） +3；低内容高粉 +3
- 增长维度：粉丝/推文比 >50 且推文 <200 +3；新号快速涨粉（<90天>500粉 +3，<30天>200粉 +4）
- 露骨卖货号不享受 marking 擦边折算；认证卖货号不享受蓝标信任加分
- 校准结果：5 个有推文数据的死亡样本全部 ≥46（该动手）；profile-only 样本输出低置信度提示

v5.4 变更（用户反馈：日均涨粉本身不是坏事，防止误伤真·爆红新号）：
- 增长类扣分（粉丝/推文比、新号快速涨粉、日均涨粉速度）增加“低互动”闸门：
  仅当账号互动可验证且确实低互动（中位赞 <5 或低赞占比 >70%）时扣分；
  互动健康（中位赞 >=5 且低赞占比 <=70%）不扣——真爆红新号互动不会低；
  无推文数据（互动不可验证）保留扣分（如 mirahangzhou，避免漏掉卖货新号）。
- “新号卖货人设组合”（注册 <90 天 + 卖货简介）不依赖互动，保持 +5。
"""
import json
import os
import re
from datetime import datetime

# ---- 配置加载（v5.1 合并自 master）：config.json 外部化关键词/阈值/校准权重 ----
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_config = {}
_thresholds = {}
_calibration = {}


def _load_config():
    global _config, _thresholds, _calibration
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _config = json.load(f)
            _thresholds = _config.get("thresholds", {})
            _calibration = _config.get("calibration", {})
        except (json.JSONDecodeError, IOError):
            pass


_load_config()
_KW = _config.get("keywords", {})
_CAL = _calibration

# 强成人词：明确性内容（用于敏感标记判定 / Tier2 / 成人占比）
STRONG_ADULT = _KW.get("strong_adult", [
    "小穴", "肉棒", "男娘", "femboy", "母狗", "唧唧", "鸡鸡", "牛牛",
    "性爱", "做爱", "自慰", "手冲", "口交", "肛交", "乳交", "足交",
    "阴蒂", "阴道", "阴茎", "龟头", "精液", "高潮", "色情", "淫荡",
    "淫乱", "骚货", "贱货", "肉便器", "母畜", "调教", "裸照", "裸体",
    "涩图", "色图", "r18", "r-18", "nsfw", "18+", "18禁", "onlyfans",
    "fansly", "制服诱惑", "内射", "无套", "群交", "援交", "约炮",
    "一夜情", "招嫖", "下海", "露出", "卖淫", "嫖",
    "sex", "nsfw", "porn", "hentai", "daddy", "kink", "bdsm", "spank",
    "selling content", "onlyfans", "fansly", "tribbing", "fisting",
])
# 软成人词：擦边/身体向（用于成人占比与上下文）
SOFT_ADULT = _KW.get("soft_adult", [
    "平胸", "女仆", "ts", "丝袜", "蕾丝", "写真", "福利", "图包",
    "胸", "奶子", "奶头", "屁股", "翘臀", "足控", "恋足", "spank",
    "dom", "sub", "私房", "包月", "订阅", "打赏", "内裤", "bra", "泳装",
])
# Tier 1 严重违规（非合意 / 未成年 / 性暴力 / 血腥剥刮）——仅保留无歧义严重词
TIER1_KEYWORDS = _KW.get("tier1_keywords", [
    "幼女", "幼男", "恋童", "恋童癖", "儿童色情", "炼铜",
    "迷奸", "诱奸", "非自愿", "性暴力", "人兽", "兽交", "犬交",
    "分尸", "剥皮", "gore", "snuff", "凌迟",
])
# “未成年/未成年人”仅在性语境共现时算 Tier 1（排除调侃/日常语境误报）
TIER1_MINOR_CONTEXT = STRONG_ADULT + _KW.get("tier1_minor_context", ["恋童", "儿童色情", "炼铜", "性", "色情", "操", "裸", "精液", "鸡巴"])
# “强奸”仅在与其他严重词共现时才算 Tier 1（排除成人角色扮演/玩具等语境）
TIER1_RAPE_CONTEXT = _KW.get("tier1_rape_context", ["未成年", "幼女", "幼男", "恋童", "儿童色情", "炼铜", "迷奸", "诱奸", "下药", "迷药", "非自愿"])
TIER1_DRUG_CONTEXT = _KW.get("tier1_drug_context", ["强奸", "迷奸", "诱奸", "轮奸", "未成年", "幼女", "恋童", "非自愿", "性暴力", "昏迷", "灌醉"])
# Tier 2 边界内容（性暗示 / 低俗羞辱 / 擦边）
TIER2_KEYWORDS = STRONG_ADULT + _KW.get("tier2_keywords", [
    "骚货", "贱货", "肉便器", "母畜", "淫", "荡妇", "烧鸡", "骚鸡",
    "白虎", "奶子", "奶头", "调教", "露出", "萝莉", "正太", "强奸", "强上",
    "去势", "阉割", "切蛋", "割鸡", "阉奴", "母狗", "骚逼", "鸡巴",
])

# ---- 第 10 维度：账号存续风险（封禁史与平台打击面）----
# 封禁/重生历史信号：账号曾因违规被平台处理，重启后再次违规 = 再封高优先级
SURVIVAL_BAN_KEYWORDS = _KW.get("survival_ban", [
    "复活版", "重生号", "重生", "被冻", "冻结",
    "重开", "復活", "旧号", "被盗号", "号被盗",
    # 第二轮校准（v4.8）：恢复“被封”类精确模式（避免裸词“被封”误报 QQ 封号）
    "大号被封", "老号被封", "账号被封", "号被封了", "秽土转生", "转生",
])
# 性交易/招嫖 + 商业变现信号（A 级=露骨明示，必须扣分）
# v5.2：拆分为“性服务明示”与“普通变现”——@Conny_vv 冻结案例显示性服务明示是强风险信号
SURVIVAL_SW_EXPLICIT = _KW.get("survival_sw_explicit", [
    "接线下", "可约", "全国可飞", "全国可✈", "莞式", "包夜", "线上一对一", "卖淫", "嫖", "援交",
    "可线下", "🉑线下", "可以约会", "可1可0", "有🚪", "prostitute", "escort",
])
SURVIVAL_SW_MONETIZE = _KW.get("survival_sw_monetize", [
    "接线下", "可约", "全国可飞", "全国可✈", "莞式", "报价",
    "课表", "口令", "好友位", "私信解锁", "涩涩基地", "包夜", "线上一对一",
    "领课表", "接单", "约炮", "门槛", "付费", "有偿", "包月", "订阅", "打赏",
    "图包", "淘宝", "店铺", "发售", "卖淫", "下单", "🛰", "微信", "支付宝",
    "红包", "定制", "1v1", "私聊", "加好友",
])
SURVIVAL_SW_KEYWORDS = SURVIVAL_SW_EXPLICIT + SURVIVAL_SW_MONETIZE
# 隐晦引流词（B 级=可辩解，不扣分，仅提示）
SURVIVAL_IMPLICIT_KEYWORDS = _KW.get("survival_implicit", [
    "电报", "tg", "加群", "可线下", "🉑线下", "私信", "找我", "加我", "解锁", "购买", "价格",
])
# 隐私侵害信号：泄露他人姓名/住址等（开盒）
SURVIVAL_DOX_KEYWORDS = _KW.get("survival_dox", ["地址是", "家庭住址", "住址"])
# 幼态/未成年误判风险：账号自述被平台识别为未成年（幼态人设+性话题=平台误杀高发区）
SURVIVAL_MINOR_MISJUDGE_KEYWORDS = _KW.get("survival_minor_misjudge", [
    "识别成未成年", "识别未成年", "被识别未成年", "像未成年", "幼年时期", "幼态", "未成年警告",
])

# ---- 第 11 维度：真人感 / 营销号形态 ----
# 生活化关键词：真人博主会有日常/个人叙事
LIFE_KEYWORDS = _KW.get("life_keywords", [
    "吃饭", "午饭", "晚饭", "早餐", "天气", "下雨", "上课", "上班", "下班",
    "实习", "考试", "作业", "累了", "好累", "朋友", "室友", "爸妈", "睡觉",
    "头疼", "感冒", "生病", "vlog", "心情", "吐槽", "生日", "放假", "回家",
    "剪头发", "逛街", "喝酒", "唱歌",
])
# 卖货/引流关键词（A 级=露骨明示，计入营销号形态）
SELL_KEYWORDS = _KW.get("sell_keywords", [
    "口令", "课表", "门槛", "好友位", "报价", "下单", "发售", "店铺",
    "淘宝", "有偿", "付费", "包月", "订阅", "打赏", "图包", "涩涩", "接单",
    "可约", "莞式", "私信解锁", "线上一对一", "接线下", "包夜", "约炮",
    "🛰", "微信", "支付宝", "红包", "定制", "1v1", "私聊", "加好友",
])
# 隐晦引流词（B 级=不扣分，仅提示）
SELL_IMPLICIT_KEYWORDS = _KW.get("sell_implicit", [
    "电报", "tg", "加群", "私信", "找我", "加我", "解锁", "可线下", "🉑线下", "购买", "价格",
])

# ---- v5.3：简介形态信号（TS/男娘卖货号标配人设）----
# 个人数据模板：身高/体重/脚码/三围/足模写真等（卖货人设，非真实日常）
BIO_DATA_PATTERNS = [
    re.compile(r"\d{3}\s*(?:cm)?\s*[^\dA-Za-z]{1,4}\d{2,3}\s*(?:kg|斤)?"),
    re.compile(r"(?:🦶|脚码|鞋码)\s*\d"),
    re.compile(r"三围[^\d]{0,4}\d"),
]
BIO_SELL_ROLE_KEYWORDS = _KW.get("bio_sell_role", ["足模", "写真模特", "模特", "福利姬", "私房照"])
# 引流到其他平台/同名可搜（卖货号标配）
BIO_DRAIN_KEYWORDS = _KW.get("bio_drain", ["dy同名", "抖音同名", "全网同名", "同名可搜", "t.me"])
# 卖货免责声明（卖货号标配话术）
BIO_DISCLAIMER_KEYWORDS = _KW.get("bio_disclaimer", ["感谢X平台", "遵守X平台规则", "遵守平台规则", "严格自律"])
# 简介明确否认卖货（真实博主自证，豁免数据模板加分）
BIO_NO_SELL_KEYWORDS = _KW.get("bio_no_sell", ["无推广", "不接推广", "无图包", "不卖图", "不接单", "不卖货"])


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
        # v5.1（合并 master）：无数据维度（api_reply/ip_network）从分母移除，避免系统性评分偏低
        excluded_dims = {"api_reply", "ip_network"}
        effective_max = sum(d["max_risk"] for k, d in dims.items() if k not in excluded_dims)
        score = max(0, min(100, round(total / effective_max * 100))) if effective_max > 0 else 0
        level = "high" if score >= 60 else "medium" if score >= 30 else "low"
        # v5.5：存活风险分（只看会不会被封，弱化合规项）
        _surv5 = self._survival_focus_score(raw_data, dims)

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
            "survival_score": _surv5["survival_score"],
            "survival_level": _surv5["survival_level"],
            "survival_raw": _surv5["survival_raw"],
            "survival_max": _surv5["survival_max"],
            "survival_breakdown": _surv5["survival_breakdown"],
            "dim_coverage": {
                "total_dimensions": len(dims),
                "effective_dimensions": len(dims) - len(excluded_dims),
                "missing_dimensions": sorted(excluded_dims),
                "score_basis": f"有效维度 {len(dims) - len(excluded_dims)}/{len(dims)}（api_reply/ip_network 无数据，从分母移除）",
            },
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
        # v5.3：账号年龄（新号快速涨粉/新号卖货人设信号共用）
        _age_days = None
        _joined = profile.get("joined") or ""
        for _fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                _jd = datetime.strptime(_joined.strip(), _fmt)
                _age_days = (datetime.utcnow() - _jd.replace(tzinfo=None)).days
                break
            except (ValueError, AttributeError):
                continue
        if _age_days is not None and _age_days < 0:
            _age_days = None
        # ---- v5.4：互动验证（增长类扣分的闸门）----
        _like_vals = []
        for _t in tweets:
            try:
                _like_vals.append(int(str(_t.get("likes") or 0).replace(",", "")))
            except Exception:
                _like_vals.append(0)
        _eng_n = len(_like_vals)
        _eng_verified = _eng_n >= 5
        _med_likes = sorted(_like_vals)[_eng_n // 2] if _like_vals else 0
        _low_like_ratio = (sum(1 for x in _like_vals if x < 5) / _eng_n) if _eng_n else 0
        _low_engagement = _eng_verified and (_med_likes < 5 or _low_like_ratio > 0.7)
        # 增长信号只在“互动不可验证”或“确实低互动”时生效
        _allow_growth = ((not _eng_verified) or _low_engagement) if bool(_CAL.get("growth_requires_low_engagement", True)) else True

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
        _sw_explicit_hits = []
        _sw_monetize_hits = []
        _dox_hits = []
        _impl_hits = []
        _minor_hits = []
        _impersonator_count = len(extra_data.get("impersonators") or [])
        for txt in _all_texts:
            _txt_low = (txt or "").lower()
            for kw in SURVIVAL_BAN_KEYWORDS:
                k = kw.lower()
                if k in _txt_low and ("无" + k) not in _txt_low and ("不" + k) not in _txt_low and kw not in _ban_hits:
                    _ban_hits.append(kw)
            for kw in SURVIVAL_SW_KEYWORDS:
                k = kw.lower()
                if ("无" + k) in _txt_low or ("不" + k) in _txt_low or kw in _sw_hits:
                    continue
                if kw == "门槛" and not re.search(r"门槛\s*\d", txt):
                    # “门槛”需与数字共现（如 门槛300/🚪门槛300），单独提问不算变现
                    continue
                if k in _txt_low:
                    _sw_hits.append(kw)
                    if kw in SURVIVAL_SW_EXPLICIT:
                        _sw_explicit_hits.append(kw)
                    else:
                        _sw_monetize_hits.append(kw)
            for kw in SURVIVAL_IMPLICIT_KEYWORDS:
                if kw in txt and not any(a in txt for a in SURVIVAL_SW_KEYWORDS) and kw not in _impl_hits:
                    _impl_hits.append(kw)
            for kw in SURVIVAL_DOX_KEYWORDS:
                if kw in txt and ("无" + kw) not in txt and ("不" + kw) not in txt and kw not in _dox_hits:
                    _dox_hits.append(kw)
            for kw in SURVIVAL_MINOR_MISJUDGE_KEYWORDS:
                if kw in txt and kw not in _minor_hits:
                    _minor_hits.append(kw)
        # 校准（v5.0/v5.1/v5.3）：权重来自 config.json calibration
        _ban_w = int(_CAL.get("ban_max_weight", 8))
        _sell_w = int(_CAL.get("sell_max_weight", 6))
        _sell_explicit_w = int(_CAL.get("sell_explicit_max_weight", 10))
        _dox_w = int(_CAL.get("dox_score", 5))
        _minor_w = int(_CAL.get("minor_score", 4))
        _imp_low = int(_CAL.get("impersonate_score_low", 2))
        _imp_high = int(_CAL.get("impersonate_score_high", 4))
        _survival_max = int(_CAL.get("survival_max", 18))
        # v5.3：🚪+数字 = 付费门槛（明示）
        _bio_text = profile.get("description") or ""
        if re.search(r"🚪\s*\d", _bio_text) and "🚪+数字" not in _sw_explicit_hits:
            _sw_explicit_hits.append("🚪+数字")
        # v5.3：简介形态信号（个人数据模板/引流/免责声明）
        _bio_no_sell = any(k in _bio_text for k in BIO_NO_SELL_KEYWORDS)
        _bio_data_hit = (any(p.search(_bio_text) for p in BIO_DATA_PATTERNS) or any(
            k in _bio_text for k in BIO_SELL_ROLE_KEYWORDS)) and not _bio_no_sell
        _bio_drain_hits = [k for k in BIO_DRAIN_KEYWORDS if k in _bio_text]
        _bio_disclaimer_hits = [k for k in BIO_DISCLAIMER_KEYWORDS if k in _bio_text]
        _bio_sell_count = sum(1 for kw in SELL_KEYWORDS if kw in _bio_text)
        # v5.3：新号卖货人设组合（<90 天 + 数据模板/卖货词/引流）——本轮封号潮高危组合
        _new_acc_seller = (_age_days is not None and _age_days < 90
                           and (_bio_data_hit or _bio_sell_count >= 1 or bool(_bio_drain_hits)))
        _fast_growth = (_age_days is not None and _age_days < 90 and followers > 200
                        and followers / max(1, _age_days) > 10)
        # v5.3：性服务明示 +5/个 上限 10；普通变现 +3/个 上限 6；简介形态加成
        _survival = (min(_ban_w, len(_ban_hits) * 4)
                     + min(_sell_explicit_w, len(_sw_explicit_hits) * 5)
                     + min(_sell_w, len(_sw_monetize_hits) * 3)
                     + (_dox_w if _dox_hits else 0))
        if _bio_data_hit:
            _survival += int(_CAL.get("bio_data_score", 4))
        if _bio_drain_hits:
            _survival += int(_CAL.get("bio_drain_score", 2))
        if _bio_disclaimer_hits:
            _survival += int(_CAL.get("bio_disclaimer_score", 2))
        if _bio_sell_count >= 3:
            _survival += int(_CAL.get("bio_pack_sell_score", 3))
        if _new_acc_seller:
            _survival += int(_CAL.get("new_acc_seller_combo", 5))
        if _fast_growth and _allow_growth:
            _survival += int(_CAL.get("growth_velocity", 3))
        if _minor_hits:
            _survival += _minor_w
        if _impersonator_count >= 6:
            _survival += _imp_high
        elif _impersonator_count >= 3:
            _survival += _imp_low
        _survival = min(_survival_max, _survival)
        _surv_issues = []
        if _ban_hits:
            _surv_issues.append(f"检测到封禁/重生史信号：{'、'.join(_ban_hits[:6])}（账号已被平台处理过，再封优先级高，+{min(8, len(_ban_hits) * 4)}）")
        if _sw_explicit_hits:
            _surv_issues.append(f"检测到性服务明示信号：{'、'.join(_sw_explicit_hits[:8])}（可约/接线下/全国可飞等，@Conny_vv 冻结案例支持高权重，+{min(_sell_explicit_w, len(_sw_explicit_hits) * 5)}）")
        if _sw_monetize_hits:
            _surv_issues.append(f"检测到商业变现信号：{'、'.join(_sw_monetize_hits[:8])}（口令/课表/好友位等，+{min(_sell_w, len(_sw_monetize_hits) * 3)}）")
        if _bio_data_hit:
            _surv_issues.append("简介含个人数据模板（身高/体重/脚码/三围/足模等，卖货人设，+4）")
        if _bio_drain_hits:
            _surv_issues.append(f"简介含跨平台引流词：{'、'.join(_bio_drain_hits)}（+2）")
        if _bio_disclaimer_hits:
            _surv_issues.append(f"简介含卖货免责声明：{'、'.join(_bio_disclaimer_hits)}（+2）")
        if _bio_sell_count >= 3:
            _surv_issues.append(f"简介含 {_bio_sell_count} 个露骨卖货词，明码标价简介（+3）")
        if _new_acc_seller:
            _surv_issues.append(f"新号（{_age_days} 天）+ 卖货人设（数据模板/卖货词/引流），本轮封号潮高危组合（+5）")
        if _fast_growth and _allow_growth:
            _surv_issues.append(f"注册 {_age_days} 天日均涨粉 {followers/_age_days:.0f}（>10/天）+ 低互动确认，增长速度异常（+3）")
        elif _fast_growth:
            _surv_issues.append(f"注册 {_age_days} 天日均涨粉 {followers/_age_days:.0f}（>10/天），但互动健康（中位赞 {_med_likes}），不按刷粉扣分")
        if _impl_hits:
            _surv_issues.append(f"检测到隐晦引流词（未扣分，仅提示）：{'、'.join(_impl_hits[:6])}")
        if _dox_hits:
            _surv_issues.append(f"检测到疑似隐私泄露/开盒信号：{'、'.join(_dox_hits[:4])}（涉他人真实信息，+5）")
        if _minor_hits:
            _surv_issues.append(f"检测到幼态/未成年误判信号：{'、'.join(_minor_hits[:4])}（幼态人设+性话题=平台误杀高发区，需人工复核，+4）")
        if _impersonator_count:
            _surv_issues.append(f"发现 {_impersonator_count} 个仿冒/近似账号（{'、'.join((extra_data.get('impersonators') or [])[:6])}），仿冒生态侵蚀粉丝，+{2 if _impersonator_count >= 3 else 4 if _impersonator_count >= 6 else 0}")
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
        _bio_sell = sum(1 for kw in SELL_KEYWORDS if kw in _bio_text)
        _bio_sell_impl = sum(1 for kw in SELL_IMPLICIT_KEYWORDS
                             if kw in _bio_text
                             and not any(a in _bio_text for a in SELL_KEYWORDS))
        _bio_explicit_hits = [kw for kw in SURVIVAL_SW_EXPLICIT if kw in _bio_text]
        if re.search(r"🚪\s*\d", _bio_text):
            _bio_explicit_hits.append("🚪+数字")
        _human_score = 0
        _human_break = {}
        _human_max = int(_CAL.get("human_max", 14))
        if _sell_ratio >= 0.5:
            _human_score += 6
            _human_break["卖货内容占比"] = f"{_sell_ratio*100:.0f}% 推文含卖货/引流词（>=50%，+6）"
        elif _sell_ratio >= 0.25:
            _human_score += 3
            _human_break["卖货内容占比"] = f"{_sell_ratio*100:.0f}% 推文含卖货/引流词（>=25%，+3）"
        else:
            _human_break["卖货内容占比"] = f"{_sell_ratio*100:.0f}% 推文含卖货/引流词（<25%，+0）"
        if _bio_sell >= 3:
            _human_score += 5
            _human_break["简介卖货"] = f"简介含 {_bio_sell} 个露骨卖货词（>=3，明码标价营销号，+5）"
        elif _bio_sell >= 1:
            _human_score += 3
            _human_break["简介卖货"] = f"简介含 {_bio_sell} 个露骨卖货词（>=1，营销号形态，+3）"
        else:
            _human_break["简介卖货"] = f"简介露骨卖货词 0 个（+0）"
        if _bio_explicit_hits:
            _human_score += 4
            _human_break["简介性服务明示"] = f"简介含性服务明示词：{'、'.join(_bio_explicit_hits[:5])}（+4）"
        if _bio_data_hit:
            _human_score += 3
            _human_break["简介数据模板"] = "简介含个人数据模板/卖货角色词（足模/写真模特等，+3）"
        if following > 0 and followers >= 500 and following / followers < 0.05:
            _human_score += int(_CAL.get("oneway_marketing_score", 4))
            _human_break["单向关注营销号"] = f"关注/粉丝 {following}/{followers} < 5%（单向营销号形态，+4）"
        if followers > 10000 and _bio_sell >= 2:
            _human_score += int(_CAL.get("bigv_sell_score", 3))
            _human_break["大V卖货"] = f"粉丝 {followers} >1万 且简介含 {_bio_sell} 个卖货词（大V变现号，+3）"
        if len(tweets) < 30 and followers > 500:
            _human_score += int(_CAL.get("low_content_high_follow", 3))
            _human_break["低内容高粉"] = f"仅抓取到 {len(tweets)} 条推文但粉丝 {followers}（低内容高粉，+3）"
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
        _human_score = max(0, min(_human_max, _human_score - _human_discount))

        # ---- 7 维度证据：Premium 状态 ----
        _prem_verified_score = int(_CAL.get("verified_score", -2))
        # v5.3：认证卖货号不享受蓝标信任加分（蓝标+明码标价 = 营销号伪装）
        _seller_verified = bool(profile.get("is_blue_verified") or profile.get("verified")) and _bio_sell >= 2
        _prem_score = (0 if _seller_verified else _prem_verified_score) if (profile.get("is_blue_verified") or profile.get("verified")) else (2 if followers > 10000 else 0)
        _prem_issues = ([f"蓝标认证 + 简介含 {_bio_sell} 个卖货词 → 认证卖货号，不享受信任加分（+0）"] if _seller_verified else
            [f"蓝标认证 → 推断开通 Premium（{_prem_verified_score} 信任加分）"] if (profile.get("is_blue_verified") or profile.get("verified")) else (
                [f"粉丝 {followers} >10K 但未见 Premium 标记（+2）"] if followers > 10000
                else [f"粉丝 {followers} <10K，Premium 维度无加分/扣分"]
            ))

        # ---- 2 维度证据：平台标记率（校准 marking 尺度）----
        _platform_mark_rate = len(flagged) / n_all
        _mark_raw = min(15, len(media_unmarked) * 3)
        _mark_score = _mark_raw
        _mark_issues = [f"{len(media_unmarked)} 条含成人关键词媒体未标记 Sensitive Media（每条 +3）"]
        # marking 折算收紧（v4.9）：平台标记率 <10% 且 NSFW 占比 <30% 才视为“平台认可的擦边尺度”
        # v5.3：露骨卖货号（简介含性服务明示或 >=2 卖货词）不享受折算——明码标价号无“擦边”可言
        _nsfw_share = (len(flagged) + len(strong_hits) + len(soft_hits)) / n_all
        # v5.3 修正：仅以简介明示判定“露骨卖货号”（推文命中的语境词不算，避免 chichi_maddy 类误伤）
        _seller_bio_clear = bool(_bio_explicit_hits) or _bio_sell >= 2
        if media_unmarked and _platform_mark_rate < 0.10 and _nsfw_share < 0.30 and not _seller_bio_clear:
            _mark_score = round(_mark_raw * 0.5)
            _mark_issues.append(f"平台整体标记率仅 {_platform_mark_rate*100:.1f}%（<10%）且 NSFW 占比 {_nsfw_share*100:.0f}%（<30%，平台认可的擦边尺度），按 50% 折算（{_mark_raw} -> {_mark_score}）")
        elif media_unmarked and _platform_mark_rate < 0.10 and _nsfw_share < 0.30 and _seller_bio_clear:
            _mark_issues.append(f"平台整体标记率仅 {_platform_mark_rate*100:.1f}%，但简介为露骨卖货号（性服务明示/卖货词 >=2），不享受擦边折算，漏标按正常规则扣分")
        elif media_unmarked:
            _mark_issues.append(f"平台整体标记率 {_platform_mark_rate*100:.1f}% 或 NSFW 占比 {_nsfw_share*100:.0f}%（>=30%，露骨内容不享受折算），漏标按正常规则扣分")
        else:
            _mark_issues = [f"{len(flagged)}/{len(tweets)} 条推文已被 X 标记敏感，无漏标"]

        # ---- 6 维度证据：关注/粉丝比与增长（v5.3 新增成长异常信号）----
        _follow_score = 4 if (following > 0 and followers > 0 and following / followers > 10) else 0
        _follow_issues = []
        if following > 0 and followers > 0 and following / followers > 10:
            _follow_issues.append(f"关注/粉丝比 {following}/{followers} >10（+4）")
        else:
            _follow_issues.append(f"关注/粉丝比 {following}/{followers} 正常")
        _statuses_cnt = _parse_int(profile.get("statuses", 0))
        _posts_cnt = _statuses_cnt if _statuses_cnt > 0 else len(tweets)
        if _posts_cnt > 0 and _posts_cnt < 200 and followers / _posts_cnt > 50 and _allow_growth:
            _follow_score += int(_CAL.get("growth_follow_per_tweet", 3))
            _follow_issues.append(f"粉丝/推文比 {followers}/{_posts_cnt} = {followers/_posts_cnt:.0f} >50 + 低互动确认（疑似刷粉/互关，+3）")
        elif _posts_cnt > 0 and _posts_cnt < 200 and followers / _posts_cnt > 50:
            _follow_issues.append(f"粉丝/推文比 {followers}/{_posts_cnt} = {followers/_posts_cnt:.0f} >50，但互动健康（中位赞 {_med_likes}），不按刷粉扣分")
        _joined = profile.get("joined") or ""
        _age_days = None
        for _fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                _jd = datetime.strptime(_joined.strip(), _fmt)
                _age_days = (datetime.utcnow() - _jd.replace(tzinfo=None)).days
                break
            except (ValueError, AttributeError):
                continue
        if _age_days is not None and _age_days >= 0:
            if _age_days < 30 and followers > 200 and _allow_growth:
                _follow_score += int(_CAL.get("new_acc_very_fast", 4))
                _follow_issues.append(f"注册仅 {_age_days} 天已 {followers} 粉（<30天>200粉）+ 低互动确认，新号快速涨粉（+4）")
            elif _age_days < 90 and followers > 500 and _allow_growth:
                _follow_score += int(_CAL.get("new_acc_fast", 3))
                _follow_issues.append(f"注册仅 {_age_days} 天已 {followers} 粉（<90天>500粉）+ 低互动确认，新号快速涨粉（+3）")
            elif _age_days is not None and _age_days < 90 and followers > 500:
                _follow_issues.append(f"注册仅 {_age_days} 天已 {followers} 粉，但互动健康（中位赞 {_med_likes}），不按刷粉扣分")
        if not _follow_issues:
            _follow_issues.append("无增长异常证据")
        _follow_score = min(8, _follow_score)

        dims = {
            # ---- 1. ACC 计划合规 (0-15) ----
            "acc_plan": {
                "label": "ACC 计划合规",
                # v5.3：近全成人账号（>90%）风险更高，按浓度分级
                "risk_score": 15 if nsfw_ratio_main > 0.9 else 12 if nsfw_ratio_main > 0.5 else 10 if nsfw_ratio_main > 0.2 else 0,
                "max_risk": 15,
                "issues": (
                    [f"主时间线 {nsfw_main}/{n_main} 条为成人/敏感内容（{nsfw_ratio_main*100:.0f}%>90%，近全成人账号，+15）",
                     "未检测到 ACC 计划成员证据，按“未加入”计分"]
                    if nsfw_ratio_main > 0.9 else
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
                "risk_score": _follow_score,
                "max_risk": 8,
                "issues": _follow_issues + ["粉丝机器人占比/关注列表封号率无法验证（计 0 分）"],
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
        if len(tweets) < 30 and followers > 500:
            d8 += int(_CAL.get("low_content_high_follow", 3))
            d8_breakdown["低内容高粉"] = f"仅抓取到 {len(tweets)} 条推文但粉丝 {followers}（低内容高粉，+3）"
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
            "risk_score": _survival, "max_risk": int(_CAL.get("survival_max", 18)),
            "issues": _surv_issues,
            "ban_hits": _ban_hits[:8],
            "sw_hits": _sw_hits[:10],
            "dox_hits": _dox_hits[:4],
            "minor_hits": _minor_hits[:5],
            "impersonator_count": _impersonator_count,
        }
        dims["human"] = {
            "label": "真人感/营销号形态",
            "risk_score": _human_score, "max_risk": int(_CAL.get("human_max", 14)),
            "issues": [f"{k}：{v}" for k, v in _human_break.items()],
            "life_ratio": round(_life_ratio, 3),
            "sell_ratio": round(_sell_ratio, 3),
            "repost_ratio": round(_repost_ratio, 3),
        }
        return dims

    def _survival_focus_score(self, raw_data, dims):
        """v5.5：存活风险分——只关注“会不会被封”，弱化成人内容/漏打码等合规项。
        依据：7 个真实死亡样本 + 8/10-8/11 封号潮（不真实行为/变现/新号组合为主因）。"""
        profile = raw_data.get("profile", {}) or {}
        tweets = raw_data.get("recent_tweets", []) or []
        followers = _parse_int(profile.get("followers_count", 0))
        following = _parse_int(profile.get("following_count", 0))
        _bio_text = profile.get("description") or ""

        # 1) 扫描简介+原创推文（同主引擎逻辑）
        _all_texts = [_bio_text] + [(t.get("text") or t.get("raw") or "") for t in tweets if not t.get("is_retweet")]
        _ban_hits, _sw_explicit_hits, _sw_monetize_hits = [], [], []
        for txt in _all_texts:
            txt_low = (txt or "").lower()
            for kw in SURVIVAL_BAN_KEYWORDS:
                k = kw.lower()
                if k in txt_low and ("无" + k) not in txt_low and ("不" + k) not in txt_low and kw not in _ban_hits:
                    _ban_hits.append(kw)
            for kw in SURVIVAL_SW_KEYWORDS:
                k = kw.lower()
                if ("无" + k) in txt_low or ("不" + k) in txt_low or kw in (_sw_explicit_hits + _sw_monetize_hits):
                    continue
                if kw == "门槛" and not re.search(r"门槛\s*\d", txt):
                    continue
                if k in txt_low:
                    if kw in SURVIVAL_SW_EXPLICIT:
                        _sw_explicit_hits.append(kw)
                    else:
                        _sw_monetize_hits.append(kw)
        if re.search(r"🚪\s*\d", _bio_text) and "🚪+数字" not in _sw_explicit_hits:
            _sw_explicit_hits.append("🚪+数字")
        _bio_no_sell = any(k in _bio_text for k in BIO_NO_SELL_KEYWORDS)
        _bio_data_hit = (any(p.search(_bio_text) for p in BIO_DATA_PATTERNS) or any(
            k in _bio_text for k in BIO_SELL_ROLE_KEYWORDS)) and not _bio_no_sell
        _bio_drain_hits = [k for k in BIO_DRAIN_KEYWORDS if k in _bio_text]
        _bio_disclaimer_hits = [k for k in BIO_DISCLAIMER_KEYWORDS if k in _bio_text]
        _bio_sell_count = sum(1 for kw in SELL_KEYWORDS if kw in _bio_text.lower())

        # 2) 年龄与互动闸门（同 v5.4）
        _age_days = None
        _joined = profile.get("joined") or ""
        for _fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                _jd = datetime.strptime(_joined.strip(), _fmt)
                _age_days = (datetime.utcnow() - _jd.replace(tzinfo=None)).days
                break
            except (ValueError, AttributeError):
                continue
        if _age_days is not None and _age_days < 0:
            _age_days = None
        _like_vals = []
        for _t in tweets:
            try:
                _like_vals.append(int(str(_t.get("likes") or 0).replace(",", "")))
            except Exception:
                _like_vals.append(0)
        _eng_n = len(_like_vals)
        _eng_verified = _eng_n >= 5
        _med_likes = sorted(_like_vals)[_eng_n // 2] if _like_vals else 0
        _low_like_ratio = (sum(1 for x in _like_vals if x < 5) / _eng_n) if _eng_n else 0
        _low_engagement = _eng_verified and (_med_likes < 5 or _low_like_ratio > 0.7)
        _allow_growth = ((not _eng_verified) or _low_engagement) if bool(_CAL.get("growth_requires_low_engagement", True)) else True

        # 3) 分值（上限合计 127，归一化到 100）
        brk = {}
        s = 0
        b = min(15, len(_ban_hits) * 5)
        if b: s += b; brk["封禁/重生史"] = f"{b}（{len(_ban_hits)} 个信号）"
        e = min(30, len(_sw_explicit_hits) * 10)
        if e: s += e; brk["性服务明示"] = f"{e}（{len(_sw_explicit_hits)} 个信号）"
        m = min(24, len(_sw_monetize_hits) * 6)
        if m: s += m; brk["商业变现"] = f"{m}（{len(_sw_monetize_hits)} 个信号）"
        f0 = 0
        if _bio_data_hit: f0 += 4
        if _bio_drain_hits: f0 += 2
        if _bio_disclaimer_hits: f0 += 2
        if _bio_sell_count >= 3: f0 += 3
        f0 = min(8, f0)
        if f0: s += f0; brk["简介卖货形态"] = str(f0)
        if _age_days is not None and _age_days < 90 and (_bio_data_hit or _bio_sell_count >= 1 or _bio_drain_hits):
            s += 10; brk["新号卖货组合"] = "10"
        g = 0
        _statuses_cnt = _parse_int(profile.get("statuses", 0))
        _posts_cnt = _statuses_cnt if _statuses_cnt > 0 else len(tweets)
        if _posts_cnt > 0 and _posts_cnt < 200 and followers / _posts_cnt > 50 and _allow_growth:
            g += 4
        if _age_days is not None and _age_days >= 0:
            if _age_days < 30 and followers > 200 and _allow_growth:
                g += 4
            elif _age_days < 90 and followers > 500 and _allow_growth:
                g += 4
            if _age_days < 90 and followers > 200 and followers / max(1, _age_days) > 10 and _allow_growth:
                g += 4
        g = min(12, g)
        if g: s += g; brk["增长异常"] = f"{g}（低互动确认）" if _allow_growth else f"{g}"
        if following > 0 and followers >= 500 and following / followers < 0.05:
            s += 5; brk["单向营销号"] = "5"
        if followers >= 5000 and _low_like_ratio > 0.7:
            s += 5; brk["低互动大号"] = "5"
        _imp = dims.get("survival", {}).get("impersonator_count", 0)
        if _imp >= 6: s += 4; brk["仿冒号"] = "4"
        elif _imp >= 3: s += 2; brk["仿冒号"] = "2"
        mk = min(6, int(dims.get("marking", {}).get("unflagged_count", 0)))
        if mk: s += mk; brk["漏打码"] = f"{mk}（弱信号）"
        t2 = int(dims.get("prohibited", {}).get("tier2_count", 0))
        if t2 >= 50: t2s = 8
        elif t2 >= 10: t2s = 6
        elif t2 >= 3: t2s = 4
        elif t2 >= 1: t2s = 2
        else: t2s = 0
        if t2s: s += t2s; brk["擦边浓度"] = str(t2s)

        score = max(0, min(100, s))
        level = "high" if score >= 60 else "medium" if score >= 46 else "low"
        return {
            "survival_score": score,
            "survival_level": level,
            "survival_raw": s,
            "survival_max": 100,
            "survival_breakdown": brk,
        }

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
