#!/usr/bin/env python3
"""
风险评估引擎：基于采集数据计算账号风险等级
精算版 v4：融合 X 成人内容账号长期存活自评表 v3（满分100分）
8 维度（v4）：
  1. ACC 成人内容创作者计划（0-15）
  2. ACC 三级标记合规（0-15）→ 替代原维度1
  3. API 自动回复合规（0-12）→ 纳入原维度3
  4. IP/网络环境合规（0-10）→ 替代原维度4
  5. Shadowban 状态（0-10）→ 新增
  6. 关注/粉丝比与增长模式（0-8）→ 新增
  7. Premium 会员等级（0-8，负分为信任加分）→ 新增
  8. 内容多样性与活跃度（0-12）→ 整合原维度3/6
原维度2（禁止内容零触碰，0-25）保留不变
"""
import re
import datetime
import math


class RiskEngine:
    def __init__(self, config):
        # 风险分：分数越高 = 风险越高
        # ≥60 = 高风险，≥30 = 中等风险，<30 = 低风险
        self.thresholds = config.get("risk_thresholds", {
            "high_score": 60,
            "medium_score": 30
        })
        self._compliance_details = {}

    def assess_account(self, raw_data, historical_data):
        """评估单个账号风险等级"""
        score = self._calculate_score(raw_data, historical_data)
        level = self._score_to_level(score)
        details = self._get_risk_details(raw_data, historical_data)
        recommendation = self._get_recommendation(level, details)
        dimensions = self._get_dimensions_v4(raw_data, historical_data)
        return {
            "score": score,
            "level": level,
            "details": details,
            "recommendation": recommendation,
            "dimensions": dimensions
        }

    def _calculate_score(self, raw_data, historical_data):
        """
        计算账号复合风险评分（0-100，精确到1分）
        v4 融合 X 成人内容账号长期存活自评表 v3：8 维度独立评分

        评分逻辑（风险分，分数越高 = 风险越高）：
        每个维度计算"扣分"（即风险暴露程度），总分 = 各维度扣分之和
        Premium 维度负分 = 信任加分（降低总分）

        v4 维度（8 维 + 原维度2）：
        1. ACC 计划合规（0-15）
        2. ACC 三级标记合规（0-15）→ 替代原维度1
        3. API 自动回复合规（0-12）→ 纳入原维度3
        4. IP/网络环境合规（0-10）→ 替代原维度4
        5. Shadowban 状态（0-10）→ 新增
        6. 关注/粉丝比与增长模式（0-8）→ 新增
        7. Premium 会员等级（0-8，负分为信任加分）→ 新增
        8. 内容多样性与活跃度（0-12）→ 整合原维度3/6
        9. 禁止内容零触碰（0-25，保留原维度2）

        总分 = 各维度风险分之和，确保与 _get_dimensions 输出完全一致。
        """
        dims = self._get_dimensions_v4(raw_data, historical_data)
        total_score = 0
        for key in ["ACC计划合规", "ACC三级标记合规", "API自动回复合规", "IP网络环境合规", "Shadowban隐限流",
                     "关注粉丝比与增长", "Premium会员等级", "内容多样性与活跃", "禁止内容零触碰"]:
            if key in dims:
                total_score += dims[key]["risk_score"]
        return min(max(round(total_score), 0), 100)

    # =========================================================================
    # 维度 1：内容标记合规（0-40 风险分）
    # =========================================================================
    def _content_marking_score(self, raw_data):
        """
        内容标记合规风险分（0-40）
        基于 X Adult Content Policy：
        - 全局开启"Mark media you post as containing material that may be sensitive"
        - 每条成人内容都必须正确标记为 Nudity/Sensitive
        风险分 = 未标记的成人内容数量 × 每条 4 分（最多 40 分）
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return 0  # 无推文，无风险

        total_tweets = len(tweets)
        adult_keywords = [
            "小穴", "肉棒", "鸡巴", "淫", "精液", "自慰", "高潮", "蜜穴", "屁穴",
            "男娘", "伪娘", "男の娘", "mtf", "ftm", "药娘", "cd", "crossdress",
            "femboy", "ts", "乳胶", "latex", "胶衣", "女仆", "假发", "cosplay",
            "spider", "金臀", "欲魅", "Gothic", "蕾丝", "丝袜", "黑丝", "白丝",
            "美腿", "玉足", "福利", "私拍", "私房", "写真", "性感", "裸体",
            "nsfw", "18+", "adult", "涩涩", "调教", "拘束", "sm", "露出",
            "颜射", "足交", "手淫", "飞机杯", "吃药", "事后",
            "援交", "约炮", "yp", "娼年",
            "插穴", "口交", "肛交", "阴道", "阴茎", "阴蒂", "大胸", "巨乳",
            "裸照", "果照", "走光", "姿势", "体位", "变态",
            "操", "干", "婊子", "骚", "操粉",
            "yp", "草粉", "上床"
        ]

        # 统计成人内容推文数量
        adult_tweets = []
        for tweet in tweets:
            if not isinstance(tweet, dict):
                continue
            text_lower = str(tweet.get("text", "")).lower()
            raw_str = str(tweet.get("raw", ""))

            has_adult_keyword = any(kw in text_lower for kw in adult_keywords)
            has_media = "https://" in raw_str or "t.co/" in raw_str

            # X 平台规则：成人内容关键词 + 媒体 = 必须标记
            if has_adult_keyword and has_media:
                is_flagged = tweet.get("is_sensitive", False) or tweet.get("possibly_sensitive", False) or tweet.get("is_nsfw", False)
                adult_tweets.append({"tweet": tweet, "is_flagged": is_flagged})

        if not adult_tweets:
            return 0  # 无成人内容，无风险

        total_adult = len(adult_tweets)
        properly_flagged = sum(1 for a in adult_tweets if a["is_flagged"])
        unflagged_count = total_adult - properly_flagged

        # 风险分 = 每条未标记扣 4 分（最多 40 分）
        return min(unflagged_count * 4, 40)

    # =========================================================================
    # 维度 2：禁止内容零触碰（0-25 风险分）
    # =========================================================================
    def _prohibited_content_score(self, raw_data):
        """
        禁止内容风险分（0-25）
        检测非合意内容、未成年人、性暴力、剥削、仇恨
        风险分 = 违规数量 × 扣分系数
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return 0  # 无推文，无风险

        total_tweets = len(tweets)

        # Tier 1 禁止内容（零容忍）
        tier1_keywords = [
            "非合意", "报复色情", "隐私泄露", "non-consensual",
            "未成年人", "14 岁", "16 岁", "minor", "child", "童",
            "性暴力", "强奸", "rape", "暴力", "割喉", "斩首",
            "物化", "剥削", "hate", "仇恨"
        ]

        # Tier 2 边界内容（borderline）
        tier2_keywords = [
            "暧昧", "暗示", "sensual", "suggestive", "borderline"
        ]

        tier1_count = 0
        tier2_count = 0

        for tweet in tweets:
            if not isinstance(tweet, dict):
                continue
            text_lower = str(tweet.get("text", "")).lower()

            for kw in tier1_keywords:
                if kw in text_lower:
                    tier1_count += 1
                    break

            for kw in tier2_keywords:
                if kw in text_lower:
                    tier2_count += 1
                    break

        # 风险分计算：
        # Tier 1 违规 1 条 → 20 分风险（扣 20 分）
        # Tier 1 违规 ≥3 条 → 25 分风险（扣完）
        # Tier 2 边界 1-2 条 → 5 分风险
        # Tier 2 边界 ≥3 条 → 10 分风险

        if tier1_count >= 3:
            return 25  # 多次违规，满分风险
        elif tier1_count >= 1:
            return 20  # 1 条 Tier1，扣 20 分
        elif tier2_count >= 3:
            return 10  # ≥3 条 Tier2，扣 10 分
        elif tier2_count >= 1:
            return 5   # 1-2 条 Tier2，扣 5 分
        else:
            return 0  # 无违规

    # =========================================================================
    # 维度 3：行为真实性与频率（0-15 风险分）
    # =========================================================================
    def _behavior_authenticity_score(self, raw_data, historical_data):
        """
        行为真实性风险分（0-15）
        检测自动化工具、发帖频率、内容重复度、engagement pods
        风险分 = 各项异常扣分之和
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return 0  # 无推文，无风险

        total_tweets = len(tweets)
        risk_score = 0

        # A. 自动化工具检测（0-15 风险分）
        bot_signals = set()
        for tweet in tweets:
            if not isinstance(tweet, dict):
                continue
            text_lower = str(tweet.get("text", "")).lower()

            # 信号：自动点赞/关注、批量操作、engagement pods
            if any(kw in text_lower for kw in [" liked ", " followed ", "你赞了", "你关注了"]):
                bot_signals.add("auto_interaction")
            # 批量操作：关键词需配合上下文，避免误报（如"自动飞机杯"不是自动化工具）
            batch_patterns = ["批量", "自动发帖", "自动转发", "自动工具", "自动发布", "自动回复", "定时发布", "定时推送"]
            if any(kw in text_lower for kw in batch_patterns):
                bot_signals.add("batch_operation")
            # "bot" 需要配合上下文（如 Twitter bot、bot 账号），避免误报
            if " bot " in text_lower or "bot 账号" in text_lower or "bot工具" in text_lower:
                bot_signals.add("batch_operation")
            # "脚本" 单独出现即命中
            if "脚本" in text_lower:
                bot_signals.add("batch_operation")
            if any(kw in text_lower for kw in ["互赞", "互关", "互粉", "engag"]):
                bot_signals.add("engagement_pod")

        # 每种自动���工具信号扣 5 分（最多 15 分）
        risk_score += min(len(bot_signals) * 5, 15)

        # B. 发帖频率突增检测（0-5 风险分）
        if historical_data:
            last_data = historical_data[-1].get("data", {})
            if isinstance(last_data, dict):
                last_tweet_count = len(last_data.get("recent_tweets", []))
                if last_tweet_count > 0:
                    freq_ratio = total_tweets / last_tweet_count
                    if freq_ratio > 2.0:  # 发帖量突增 2 倍以上
                        risk_score += min(int((freq_ratio - 2.0) * 10), 5)

        # C. 内容重复度检测（0-7.5 风险分）
        unique_texts = set()
        for tweet in tweets:
            if isinstance(tweet, dict):
                unique_texts.add(str(tweet.get("text", "")))

        repeat_ratio = 1.0 - (len(unique_texts) / total_tweets)
        if repeat_ratio > 0.3:  # 重复内容 > 30%
            risk_score += min(round(repeat_ratio * 7.5), 8)

        # D. 短时间密集发布检测（0-5 风险分）
        dates = []
        for tweet in tweets:
            if isinstance(tweet, dict) and tweet.get("datetime"):
                try:
                    dt = datetime.datetime.fromisoformat(tweet["datetime"].replace("Z", "+00:00"))
                    dates.append(dt)
                except:
                    pass

        if len(dates) >= 10:
            dates.sort()
            # 检测 24 小时内推文占比
            one_day = datetime.timedelta(days=1)
            recent_tweets = sum(1 for d in dates if (dates[-1] - d) <= one_day)
            daily_ratio = recent_tweets / len(dates)
            if daily_ratio > 0.5:  # 50% 推文在 24 小时内
                risk_score += min(round((daily_ratio - 0.5) * 10), 5)

        return min(risk_score, 15)

    # =========================================================================
    # 维度 4：账号环境与登录安全（0-10 风险分）
    # =========================================================================
    def _account_environment_score(self, raw_data):
        """
        账号环境与登录安全风险分（0-10）
        检测干净设备/稳定 IP/绑定手机号/正常活跃
        风险分 = 各项问题扣分之和
        """
        profile = raw_data.get("profile", {})
        account_status = raw_data.get("account_status", {})
        risk_score = 0

        # A. 新号检测（0-3 风险分）
        if isinstance(profile, dict) and profile:
            followers_count = profile.get("followers_count", 0)
            if followers_count < 100:
                risk_score += 3  # 新号，高风险
        # 如果 profile 为空字典（未采集到），跳过此检查

        # B. 异常登录（0-3 风险分）
        if isinstance(account_status, dict):
            if account_status.get("suspicious_login"):
                risk_score += 3

        # C. Banner NSFW 检测（2026-07-26 新增，基于用户反馈）
        # X 官方规则：成人内容账号不应放裸图在 Profile/Banner
        banner_keywords = ["裸体", "裸", "性感", "福利", "写真", "cosplay", "丝袜", "黑丝", "女仆", "乳胶", "巨乳", "大胸"]
        banner_text = str(profile.get("banner_text", "") + profile.get("banner_description", "")).lower()
        banner_has_media = "https://" in str(profile.get("banner_url", ""))
        if banner_has_media and any(kw in banner_text for kw in banner_keywords):
            risk_score += 2

        # D. 脏设备/IP（0-2 风险分）
        if isinstance(account_status, dict):
            if account_status.get("dirty_device") or account_status.get("shared_ip"):
                risk_score += 2

        # D. 未绑定手机号（0-2 风险分）
        if isinstance(account_status, dict):
            if account_status.get("needs_verification"):
                risk_score += 2

        return min(risk_score, 10)

    # =========================================================================
    # 维度 5：举报与历史记录（0-5 风险分）
    # =========================================================================
    def _report_history_score(self, raw_data):
        """
        举报与历史记录风险分（0-5）
        检测用户举报量、历史警告、正式违规记录
        风险分 = 各项问题扣分之和
        """
        account_status = raw_data.get("account_status", {})
        risk_score = 0

        if isinstance(account_status, dict):
            # 多次被举报
            if account_status.get("report_count", 0) > 5:
                risk_score += 3

            # 有正式警告记录
            if account_status.get("has_warning"):
                risk_score += 2

            # 多次正式违规
            if account_status.get("violation_count", 0) >= 3:
                risk_score += 5  # 扣完

        return min(risk_score, 5)

    # =========================================================================
    # 维度 6：其他规则合规（0-5 风险分）
    # =========================================================================
    def _other_compliance_score(self, raw_data):
        """
        其他规则合规风险分（0-5）
        检测骚扰、冒充、版权侵权、平台操纵、非法引流
        风险分 = 违规类型数量 × 1 分（最多 5 分）
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return 0  # 无推文，无风险

        total_tweets = len(tweets)
        violations = 0

        for tweet in tweets:
            if not isinstance(tweet, dict):
                continue
            text_lower = str(tweet.get("text", "")).lower()

            # 骚扰
            if any(kw in text_lower for kw in ["@user1 @user2 @user3", "批量@", "刷屏"]):
                violations += 1

            # 版权侵权
            if any(kw in text_lower for kw in ["版权", "copyright", "music", "unauthorized"]):
                violations += 1

            # 冒充
            if any(kw in text_lower for kw in ["imperson", "冒充", "official"]):
                violations += 1

            # 平台操纵
            if any(kw in text_lower for kw in ["刷量", "bot", "engagement pod"]):
                violations += 1

        # 风险分 = 违规类型数量 × 1 分（最多 5 分）
        return min(violations, 5)

    # =========================================================================
    # 维度详情提取（用于报告展示）
    # =========================================================================
    def _get_dimensions_v4(self, raw_data, historical_data):
        """
        v4 维度评估：返回 9 个维度的详细分数（中文键名）
        """
        dimension_scores = {}
        tweets = raw_data.get("recent_tweets", [])
        profile = raw_data.get("profile", {})
        account_status = raw_data.get("account_status", {})
        historical_data = historical_data if historical_data else []

        # 维度1：ACC 计划
        dimension_scores["ACC计划合规"] = self._acc_program_score(raw_data)
        # 维度2：ACC 三级标记
        dimension_scores["ACC三级标记合规"] = self._acc_marking_score(raw_data)
        # 维度3：API 回复
        dimension_scores["API自动回复合规"] = self._api_reply_score(raw_data)
        # 维度4：IP 网络
        dimension_scores["IP网络环境合规"] = self._ip_network_score(raw_data)
        # 维度5：Shadowban
        dimension_scores["Shadowban隐限流"] = self._shadowban_score(raw_data)
        # 维度6：关注/粉丝比
        dimension_scores["关注粉丝比与增长"] = self._follow_ratio_score(raw_data)
        # 维度7：Premium
        dimension_scores["Premium会员等级"] = self._premium_score(raw_data)
        # 维度8：内容多样性
        dimension_scores["内容多样性与活跃"] = self._content_diversity_score(raw_data, historical_data)
        # 维度9：禁止内容（保留原逻辑）
        dimension_scores["禁止内容零触碰"] = {"risk_score": self._prohibited_content_score(raw_data), "max_risk": 25,
                                          "details": "保留原维度2逻辑"}
        return dimension_scores

    def _get_dimensions(self, raw_data, historical_data):
        """
        v3 维度评估（向后兼容）
        每个维度独立评分，总分 = 各维度得分之和（精确到1分）。
        扣分标准清晰可见，确保 _calculate_score 和 _get_dimensions 输出完全一致。
        """
        dimension_scores = {}
        tweets = raw_data.get("recent_tweets", [])
        profile = raw_data.get("profile", {})
        account_status = raw_data.get("account_status", {})
        historical_data = historical_data if historical_data else []

        # =========================================================================
        # 维度 1：内容标记合规（0-40 风险分）
        # 标准：成人内容推文是否正确标记 is_sensitive/possibly_sensitive
        # 风险分：每条未标记的成人内容推文加 4 分风险（最多 40 分）
        # =========================================================================
        adult_keywords = ["小穴", "肉棒", "鸡巴", "淫", "精液", "自慰", "高潮", "蜜穴", "屁穴",
            "男娘", "伪娘", "男の娘", "mtf", "ftm", "药娘", "cd", "crossdress",
            "femboy", "ts", "乳胶", "latex", "胶衣", "女仆", "假发", "cosplay",
            "spider", "金臀", "欲魅", "Gothic", "蕾丝", "丝袜", "黑丝", "白丝",
            "美腿", "玉足", "福利", "私拍", "私房", "写真", "性感", "裸体",
            "nsfw", "18+", "adult", "涩涩", "调教", "拘束", "sm", "露出",
            "颜射", "足交", "手淫", "飞机杯", "吃药", "事后",
            "援交", "约炮", "yp", "娼年",
            "插穴", "口交", "肛交", "阴道", "阴茎", "阴蒂", "大胸", "巨乳",
            "裸照", "果照", "走光", "姿势", "体位", "变态",
            "操", "干", "婊子", "骚", "操粉",
            "yp", "草粉", "上床"]
        adult_tweets = []
        for t in tweets:
            if not isinstance(t, dict):
                continue
            text_lower = str(t.get("text", "")).lower()
            has_adult = any(kw in text_lower for kw in adult_keywords)
            has_media = "https://" in str(t.get("raw", "")) or "t.co/" in str(t.get("raw", ""))
            if has_adult and has_media:
                is_flagged = t.get("is_sensitive", False) or t.get("possibly_sensitive", False) or t.get("is_nsfw", False)
                adult_tweets.append({"is_flagged": is_flagged})

        total_adult = len(adult_tweets)
        flagged = sum(1 for a in adult_tweets if a["is_flagged"])
        unflagged = total_adult - flagged

        if total_adult == 0:
            marking_risk = 0
        else:
            # 每条未标记加 4 分风险（最多 40 分）
            marking_risk = min(unflagged * 4, 40)

        dimension_scores["marking"] = {
            "risk_score": marking_risk,
            "max_risk": 40,
            "total_adult_tweets": total_adult,
            "flagged_count": flagged,
            "unflagged_count": unflagged,
            "deduction_per_tweet": 4,
            "issues": [f"⚠️ {unflagged} 条成人内容推文未标记 Sensitive Media"] if unflagged > 0 else []
        }

        # =========================================================================
        # 维度 2：禁止内容零触碰（满分 25 分）
        # 标准：无非合意/未成年人/性暴力/剥削内容
        # 扣分：Tier 1 违规 1 条扣 20 分（得 5 分），≥3 条扣完（得 0 分）
        #        Tier 2 边界内容 1-2 条扣 5 分，≥3 条扣 10 分
        # =========================================================================
        tier1_keywords = ["非合意", "报复色情", "隐私泄露", "non-consensual", "未成年人", "14 岁", "16 岁",
                          "minor", "child", "童", "性暴力", "强奸", "rape", "暴力", "割喉", "斩首",
                          "物化", "剥削", "hate", "仇恨"]
        tier2_keywords = ["暧昧", "暗示", "sensual", "suggestive", "borderline"]

        tier1_count = 0
        tier2_count = 0
        tier1_details = []
        for t in tweets:
            if not isinstance(t, dict):
                continue
            text_lower = str(t.get("text", "")).lower()
            for kw in tier1_keywords:
                if kw in text_lower:
                    tier1_count += 1
                    tier1_details.append(kw)
                    break
            for kw in tier2_keywords:
                if kw in text_lower:
                    tier2_count += 1
                    break

        if tier1_count >= 3:
            prohibited_risk = 25
        elif tier1_count >= 1:
            prohibited_risk = 20
        elif tier2_count >= 3:
            prohibited_risk = 10
        elif tier2_count >= 1:
            prohibited_risk = 5
        else:
            prohibited_risk = 0

        dimension_scores["prohibited"] = {
            "risk_score": prohibited_risk,
            "max_risk": 25,
            "tier1_violations": tier1_count,
            "tier1_details": tier1_details[:3],
            "tier2_count": tier2_count,
            "deduction_rules": {
                "tier1_1条": "加20分风险",
                "tier1_≥3条": "加25分风险",
                "tier2_1-2条": "加5分风险",
                "tier2_≥3条": "加10分风险"
            },
            "issues": [f"⚠️ Tier1违规: {', '.join(tier1_details[:3])}"] if tier1_count > 0 else ([] if tier2_count == 0 else [f"ℹ️ Tier2边界内容 {tier2_count} 条"])
        }

        # =========================================================================
        # 维度 3：行为真实性与频率（满分 15 分）
        # 标准：手动操作、频率自然、无刷量
        # 扣分：自动化工具信号每种扣 5 分（最多扣 15 分）
        #        发帖频率突增 2 倍以上扣 5 分
        #        内容重复率 >30% 按重复率比例扣（最多扣 7.5 分）
        #        24小时内密集发布（>50%推文在24h内）按超出版比扣（最多扣 5 分）
        # =========================================================================
        bot_signal_types = set()
        for t in tweets:
            if not isinstance(t, dict):
                continue
            text_lower = str(t.get("text", "")).lower()
            if any(kw in text_lower for kw in [" liked ", " followed ", "你赞了", "你关注了"]):
                bot_signal_types.add("auto_interaction")
            # 批量操作：关键词需配合上下文，避免误报（如"自动飞机杯"不是自动化工具）
            batch_patterns = ["批量", "自动发帖", "自动转发", "自动工具", "自动发布", "自动回复", "定时发布", "定时推送"]
            if any(kw in text_lower for kw in batch_patterns):
                bot_signal_types.add("batch_operation")
            if " bot " in text_lower or "bot 账号" in text_lower or "bot工具" in text_lower:
                bot_signal_types.add("batch_operation")
            if "脚本" in text_lower:
                bot_signal_types.add("batch_operation")
            if any(kw in text_lower for kw in ["互赞", "互关", "互粉", "engag"]):
                bot_signal_types.add("engagement_pod")

        behavior_risk = 0
        behavior_issues = []

        # 自动化工具风险
        bot_penalty = len(bot_signal_types) * 5
        behavior_risk += bot_penalty
        if bot_signal_types:
            behavior_issues.append(f"⚠️ 检测到 {len(bot_signal_types)} 种自动化工具信号: {', '.join(bot_signal_types)}")

        # 发帖频率突增
        if historical_data:
            last_data = historical_data[-1].get("data", {})
            if isinstance(last_data, dict):
                last_tweet_count = len(last_data.get("recent_tweets", []))
                if last_tweet_count > 0:
                    freq_ratio = len(tweets) / last_tweet_count
                    if freq_ratio > 2.0:
                        penalty = min(int((freq_ratio - 2.0) * 10), 5)
                        behavior_risk += penalty
                        behavior_issues.append(f"⚠️ 发帖频率突增 {freq_ratio:.1f} 倍，加 {penalty} 分风险")

        # 内容重复率
        unique_texts = set()
        for t in tweets:
            if isinstance(t, dict):
                unique_texts.add(str(t.get("text", "")))
        repeat_ratio = 1.0 - (len(unique_texts) / len(tweets)) if tweets else 0
        if repeat_ratio > 0.3:
            penalty = min(round(repeat_ratio * 7.5), 8)
            behavior_risk += penalty
            behavior_issues.append(f"⚠️ 内容重复率 {repeat_ratio:.0%}，加 {penalty} 分风险")

        # 24小时密集发布
        dates = []
        for t in tweets:
            if isinstance(t, dict) and t.get("datetime"):
                try:
                    dt = datetime.datetime.fromisoformat(t["datetime"].replace("Z", "+00:00"))
                    dates.append(dt)
                except:
                    pass
        if len(dates) >= 10:
            dates.sort()
            one_day = datetime.timedelta(days=1)
            recent_in_24h = sum(1 for d in dates if (dates[-1] - d) <= one_day)
            daily_ratio = recent_in_24h / len(dates)
            if daily_ratio > 0.5:
                penalty = min(round((daily_ratio - 0.5) * 10), 5)
                behavior_risk += penalty
                behavior_issues.append(f"⚠️ {recent_in_24h}/{len(dates)} 条推文在24小时内，加 {penalty} 分风险")

        # =========================================================================
        # 转贴模式异常检测（2026-07-26 新增）
        # 政策依据：X 反 Spam 规则——大量、重复的转贴行为触发"非真实行为"判定
        # 不重复扣"内容风险"（已在内容标记合规中计算），只评估"行为模式风险"
        # =========================================================================
        retweets = []
        originals = []
        for t in tweets:
            if isinstance(t, dict):
                if t.get("is_retweet"):
                    retweets.append(t)
                else:
                    originals.append(t)

        total_tweets = len(tweets)
        retweet_count = len(retweets)
        original_count = len(originals)
        retweet_ratio = retweet_count / total_tweets if total_tweets else 0

        # 转贴中的成人内容（用同一份关键词列表）
        adult_kws_for_rt = adult_keywords
        retweet_adult_count = sum(
            1 for t in retweets
            if any(kw in str(t.get("text", "")).lower() for kw in adult_kws_for_rt)
        )
        retweet_adult_ratio = retweet_adult_count / retweet_count if retweet_count else 0

        # 信号1：NSFW 转贴占比 >50%
        if retweet_count >= 3 and retweet_adult_ratio > 0.5:
            behavior_risk += 3
            behavior_issues.append(f"⚠️ 转贴中 {retweet_adult_count}/{retweet_count} 条含成人内容 ({retweet_adult_ratio:.0%})，疑似 NSFW 搬运号")

        # 信号2：账号几乎只转不原创
        if total_tweets >= 5 and retweet_ratio > 0.8 and original_count < total_tweets * 0.2:
            behavior_risk += 5
            behavior_issues.append(f"⚠️ 账号转贴占比 {retweet_ratio:.0%}（{retweet_count}/{total_tweets}），原创极低")

        # 信号3：转贴中 NSFW 标签高度集中
        nsfw_tag_count = 0
        for t in retweets:
            text = str(t.get("text", ""))
            # 检查 NSFW 相关标签
            if any(tag in text.lower() for tag in ["#nsfw", "#18+", "#成人", "#色情", "#r18"]):
                nsfw_tag_count += 1
        if nsfw_tag_count >= 3:
            behavior_risk += 2
            behavior_issues.append(f"⚠️ 转贴中 {nsfw_tag_count} 条带 NSFW/18+ 标签，内容高度集中")

        # 信号4：互动信号缺失（转贴 >50% 且无明显互动）
        if retweet_ratio > 0.5:
            avg_likes = sum(t.get("likes", 0) for t in tweets if isinstance(t, dict)) / total_tweets if total_tweets else 0
            if avg_likes < 5 and total_tweets >= 10:
                behavior_risk += 2
                behavior_issues.append(f"⚠️ 转贴占比高 ({retweet_ratio:.0%}) 且互动低 (平均 {avg_likes:.1f} 赞)，疑似低质搬运")

        # 信号5：硬转推占比分级扣分（2026-07-26 新增，基于用户反馈）
        # 政策依据：新版X显示"已转帖"标记，硬转推 ≠ 原创内容
        if total_tweets >= 5:
            if retweet_ratio > 0.8:
                behavior_risk += 5
                behavior_issues.append(f"⚠️ 硬转推占比极高 ({retweet_ratio:.0%})，疑似纯搬运号，加 5 分风险")
            elif retweet_ratio > 0.5:
                behavior_risk += 3
                behavior_issues.append(f"⚠️ 硬转推占比高 ({retweet_ratio:.0%})，加 3 分风险")

        # 信号6：时间间隔均匀度检测（2026-07-26 新增）
        # 检测程序化自动回复/自动发推：推文时间间隔完全一致
        if len(dates) >= 5:
            intervals = []
            for i in range(1, len(dates)):
                delta = dates[i] - dates[i-1]
                intervals.append(delta.total_seconds())
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                if avg_interval > 0:
                    # 计算间隔变异系数（标准差/均值）
                    variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                    std_dev = variance ** 0.5
                    cv = std_dev / avg_interval if avg_interval > 0 else 999
                    # CV < 0.05 = 间隔几乎完全一致 → 程序化发推
                    if cv < 0.05 and len(intervals) >= 5:
                        behavior_risk += 2
                        behavior_issues.append(f"⚠️ 推文时间间隔几乎完全一致 (变异系数 {cv:.4f})，疑似程序化发推/自动回复")

        behavior_risk = min(behavior_risk, 15)
        if not behavior_issues:
            behavior_issues.append("✅ 行为自然，无明显异常")

        dimension_scores["behavior"] = {
            "risk_score": behavior_risk,
            "max_risk": 15,
            "bot_signal_types": list(bot_signal_types),
            "behavior_issues": behavior_issues,
            "deduction_breakdown": {
                "自动化工具": f"{len(bot_signal_types)} 种 × 5分 = {len(bot_signal_types) * 5}分风险",
                "频率突增": "视倍数加分（最多5分风险）",
                "内容重复": f"重复率 {repeat_ratio:.0%} → 加 {min(round(repeat_ratio * 7.5), 8)} 分风险" if repeat_ratio > 0.3 else "无",
                "密集发布": "",
                "硬转推占比": ">50%加3分风险，>80%加5分风险（2026-07-26新增）",
                "时间均匀度": "CV<0.05加2分风险（2026-07-26新增）"
            }
        }

        # =========================================================================
        # 维度 4：账号环境与登录安全（满分 10 分）
        # 标准：干净设备/稳定IP/绑定手机/正常活跃
        # 扣分：新号（粉丝<100）扣 3 分
        #        Banner NSFW 扣 2 分（2026-07-26 新增）
        #        异常登录扣 3 分
        #        脏设备/共享IP扣 2 分
        #        未绑定手机扣 2 分
        # =========================================================================
        env_risk = 0
        env_issues = []

        if isinstance(profile, dict) and profile and profile.get("followers_count", 0) < 100:
            env_risk += 3
            env_issues.append("⚠️ 新号（粉丝 < 100），加 3 分风险")

        # Banner NSFW 检测（2026-07-26 新增，基于用户反馈）
        banner_keywords = ["裸体", "裸", "性感", "福利", "写真", "cosplay", "丝袜", "黑丝", "女仆", "乳胶", "巨乳", "大胸"]
        banner_text = str(profile.get("banner_text", "") + profile.get("banner_description", "")).lower()
        banner_has_media = "https://" in str(profile.get("banner_url", ""))
        if banner_has_media and any(kw in banner_text for kw in banner_keywords):
            env_risk += 2
            env_issues.append("⚠️ Profile/Banner 含 NSFW 内容，加 2 分风险")

        if isinstance(account_status, dict):
            if account_status.get("suspicious_login"):
                env_risk += 3
                env_issues.append("⚠️ 异常登录，加 3 分风险")
            if account_status.get("dirty_device") or account_status.get("shared_ip"):
                env_risk += 2
                env_issues.append("⚠️ 脏设备/共享IP，加 2 分风险")
            if account_status.get("needs_verification"):
                env_risk += 2
                env_issues.append("⚠️ 未绑定手机/需验证，加 2 分风险")

        env_risk = min(env_risk, 10)
        if not env_issues:
            env_issues.append("✅ 账号环境正常")

        dimension_scores["environment"] = {
            "risk_score": env_risk,
            "max_risk": 10,
            "issues": env_issues,
            "deduction_rules": {
                "新号(粉丝<100)": "加3分风险",
                "Banner NSFW": "加2分风险（2026-07-26新增）",
                "异常登录": "加3分风险",
                "脏设备/共享IP": "加2分风险",
                "未绑定手机": "加2分风险"
            }
        }

        # =========================================================================
        # 维度 5：举报与历史记录（满分 5 分）
        # 标准：无举报/无警告/无正式违规
        # 扣分：举报 >5 次扣 3 分
        #        有警告记录扣 2 分
        #        违规次数 ≥3 扣完 5 分
        # =========================================================================
        report_risk = 0
        report_issues = []

        if isinstance(account_status, dict):
            if account_status.get("report_count", 0) > 5:
                report_risk += 3
                report_issues.append("⚠️ 举报次数 > 5，加 3 分风险")
            if account_status.get("has_warning"):
                report_risk += 2
                report_issues.append("⚠️ 有警告记录，加 2 分风险")
            if account_status.get("violation_count", 0) >= 3:
                report_risk += 5
                report_issues.append("⚠️ 违规次数 ≥ 3，加 5 分风险")

        report_risk = min(report_risk, 5)
        if not report_issues:
            report_issues.append("✅ 无举报/警告记录")

        dimension_scores["report_history"] = {
            "risk_score": report_risk,
            "max_risk": 5,
            "issues": report_issues,
            "deduction_rules": {
                "举报>5次": "加3分风险",
                "有警告记录": "加2分风险",
                "违规≥3次": "加5分风险"
            }
        }

        # =========================================================================
        # 维度 6：其他规则合规（满分 5 分）
        # 标准：无骚扰/冒充/版权/平台操纵
        # 扣分：发现违规内容每条扣 1 分，最多扣 5 分
        # =========================================================================
        other_risk = 0
        other_issues = []
        violation_keywords = {
            "骚扰": ["@user1 @user2 @user3", "批量@", "刷屏"],
            "版权": ["版权", "copyright", "music", "unauthorized"],
            "冒充": ["imperson", "冒充", "official"],
            "平台操纵": ["刷量", "bot", "engagement pod"]
        }
        found_violations = []
        for t in tweets:
            if not isinstance(t, dict):
                continue
            text_lower = str(t.get("text", "")).lower()
            for violation_type, kws in violation_keywords.items():
                if any(kw in text_lower for kw in kws):
                    if violation_type not in found_violations:
                        found_violations.append(violation_type)

        if found_violations:
            other_risk = min(len(found_violations), 5)
            other_issues.append(f"⚠️ 发现 {len(found_violations)} 类违规: {', '.join(found_violations)}，加 {other_risk} 分风险")
        else:
            other_issues.append("✅ 其他规则合规")

        dimension_scores["other_compliance"] = {
            "risk_score": other_risk,
            "max_risk": 5,
            "issues": other_issues,
            "violations_found": found_violations,
            "deduction_rules": {
                "每类违规": "加1分风险（最多5分）"
            }
        }

        return dimension_scores

    # =========================================================================
    # 原有辅助方法
    # =========================================================================
    def _score_to_level(self, score):
        """分数转等级（风险分：分数越高 = 风险越高）"""
        if score >= self.thresholds["high_score"]:
            return "high"
        elif score >= self.thresholds["medium_score"]:
            return "medium"
        else:
            return "low"

    def _get_risk_details(self, raw_data, historical_data):
        """获取风险详情"""
        details = []
        account_status = raw_data.get("account_status", {})

        # 账号状态
        if isinstance(account_status, dict):
            if account_status.get("is_suspended"):
                details.append("账号状态异常: 已封禁")
            elif account_status.get("is_frozen"):
                details.append("账号状态异常: 已冻结")

        # 推文分析
        tweets = raw_data.get("recent_tweets", [])
        if tweets:
            details.append(f"已分析 {len(tweets)} 篇最近推文")

            # X 平台成人内容标记检测
            adult_keywords = ["小穴", "肉棒", "鸡巴", "淫", "精液", "男娘", "femboy", "ts", "乳胶", "女仆"]
            unflagged_adult = []
            for t in tweets:
                if not isinstance(t, dict):
                    continue
                text_lower = str(t.get("text", "")).lower()
                has_media = "https://" in str(t.get("raw", "")) or "t.co/" in str(t.get("raw", ""))
                is_adult = any(kw in text_lower for kw in adult_keywords) and has_media
                is_flagged = t.get("is_sensitive", False) or t.get("possibly_sensitive", False)
                if is_adult and not is_flagged:
                    unflagged_adult.append(t)

            if unflagged_adult:
                details.append(f"⚠️ X 平台警告：{len(unflagged_adult)} 条成人内容推文未标记 'Sensitive Media'（可能被限流）")

            # 转发检测
            retweet_count = sum(1 for t in tweets if isinstance(t, dict) and t.get("is_retweet"))
            if retweet_count > 0:
                details.append(f"检测到 {retweet_count} 篇转发推文")

            # 原创度
            original_count = sum(1 for t in tweets if isinstance(t, dict) and not t.get("is_retweet", False))
            if len(tweets) >= 5:
                details.append(f"原创度: {original_count}/{len(tweets)} ({original_count/len(tweets)*100:.1f}%)")

        # 维度详情
        dimensions = self._get_dimensions(raw_data, historical_data)
        if "marking" in dimensions and dimensions["marking"].get("unflagged_count", 0) > 0:
            details.append(f"内容标记合规: {dimensions['marking'].get('flagged_count', 0)}/{dimensions['marking'].get('total_adult_tweets', 0)} 条已标记")

        return details

    def _get_recommendation(self, level, details):
        """获取建议"""
        if level == "high":
            return "高风险：建议立即检查账号状态，查看是否有违规推文需要删除，重点检查 NSFW 内容是否标记敏感"
        elif level == "medium":
            return "中等风险：建议关注账号状态变化，定期检查推文内容，适当提升原创比例"
        else:
            return "正常：账号状态良好，继续监控即可"

    # =========================================================================
    # v4 新增维度函数
    # =========================================================================

    def _acc_program_score(self, raw_data):
        """
        维度1：ACC 成人内容创作者计划合规（0-15 风险分）
        政策依据：X Adult Content Policy 2026 — 所有发布成人内容的账号必须加入 ACC
        """
        account_status = raw_data.get("account_status", {})
        profile = raw_data.get("profile", {})
        risk_score = 0
        issues = []

        if isinstance(account_status, dict):
            acc_status = account_status.get("acc_status", "unknown")

            if acc_status == "not_enrolled":
                # 未加入 ACC
                risk_score = 10
                issues.append("⚠️ 未加入 ACC 成人内容创作者计划（2026 强制要求），加 10 分风险")
            elif acc_status == "enrolled_incomplete":
                # 已加入但未完善资料
                risk_score = 7
                issues.append("⚠️ ACC 资料不完整（缺 ID/税单），加 7 分风险")
            elif acc_status == "enrolled_complete":
                # 已完善
                risk_score = 0
                issues.append("✅ ACC 计划已完善（含身份验证和税务信息）")
            else:
                # unknown — 无法判断
                risk_score = 5
                issues.append("ℹ️ ACC 状态未知，默认加 5 分风险")

        return {"risk_score": risk_score, "max_risk": 15, "issues": issues,
                "acc_status": account_status.get("acc_status", "unknown") if isinstance(account_status, dict) else "unknown"}

    def _acc_marking_score(self, raw_data):
        """
        维度2：ACC 三级标记 + 基础标记合规（0-15 风险分）
        政策依据：ACC 三级分类必须匹配内容等级（Sensitive/Adult/Explicit）
        同时检测未标记的成人内容（v3 基础标记检测）
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return {"risk_score": 0, "max_risk": 15, "issues": ["✅ 无推文，无标记风险"]}

        adult_keywords = ["小穴", "肉棒", "鸡巴", "淫", "精液", "自慰", "高潮", "蜜穴", "屁穴",
            "男娘", "伪娘", "男の娘", "mtf", "ftm", "药娘", "cd", "crossdress",
            "femboy", "ts", "乳胶", "latex", "胶衣", "女仆", "假发", "cosplay",
            "nsfw", "18+", "adult", "涩涩", "调教", "拘束", "sm", "露出",
            "颜射", "足交", "手淫", "飞机杯", "吃药", "事后",
            "援交", "约炮", "yp", "插穴", "口交", "肛交", "阴道", "阴茎", "阴蒂", "大胸", "巨乳",
            "裸照", "果照", "走光", "姿势", "体位", "操", "干", "婊子", "骚", "操粉", "草粉", "上床"]

        # 基础标记检测：成人内容+媒体 = 必须标记
        unflagged_count = 0
        for t in tweets:
            if not isinstance(t, dict):
                continue
            text_lower = str(t.get("text", "")).lower()
            raw_str = str(t.get("raw", ""))
            has_adult = any(kw in text_lower for kw in adult_keywords)
            has_media = "https://" in raw_str or "t.co/" in raw_str
            if has_adult and has_media:
                is_flagged = t.get("is_sensitive", False) or t.get("possibly_sensitive", False) or t.get("is_nsfw", False)
                if not is_flagged:
                    unflagged_count += 1

        risk_score = min(unflagged_count * 3, 15)
        issues = [f"⚠️ {unflagged_count} 条成人内容未标记 Sensitive Media" if unflagged_count > 0 else "✅ 三级标记合规"]
        return {"risk_score": risk_score, "max_risk": 15, "issues": issues, "unflagged_count": unflagged_count}

    def _api_reply_score(self, raw_data):
        """
        维度3：API 自动回复合规（0-12 风险分）
        政策依据：API v2 2026 — 自动回复必须提及或引用原作者
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return {"risk_score": 0, "max_risk": 12, "issues": ["✅ 无推文，无回复风险"]}

        risk_score = 0
        issues = []
        reply_tweets = [t for t in tweets if isinstance(t, dict) and t.get("is_reply", False)]

        if len(reply_tweets) > 0:
            # 检查回复是否提及/引用原作者
            unmentioned_replies = sum(1 for t in reply_tweets if not t.get("mentions_author", True))
            if unmentioned_replies > 0:
                risk_score += min(unmentioned_replies * 3, 9)
                issues.append(f"⚠️ {unmentioned_replies} 条自动回复未提及/引用原作者，加 {min(unmentioned_replies * 3, 9)} 分风险")

            # 检查同一推文被回复次数
            reply_to_counts = {}
            for t in reply_tweets:
                reply_to = t.get("reply_to_tweet_id", "")
                if reply_to:
                    reply_to_counts[reply_to] = reply_to_counts.get(reply_to, 0) + 1
            high_reply_tweets = sum(1 for v in reply_to_counts.values() if v > 10)
            if high_reply_tweets > 0:
                risk_score += min(high_reply_tweets * 2, 6)
                issues.append(f"⚠️ {high_reply_tweets} 条推文被回复 >10 次，加 {min(high_reply_tweets * 2, 6)} 分风险")

            # 检查回复内容重复
            reply_texts = [str(t.get("text", "")) for t in reply_tweets]
            unique_reply_texts = set(reply_texts)
            if len(reply_texts) - len(unique_reply_texts) > 5:
                risk_score += 3
                issues.append("⚠️ 自动回复内容完全相同（>5 条），加 3 分风险")

        risk_score = min(risk_score, 12)
        if not issues:
            issues.append("✅ API 回复合规")
        return {"risk_score": risk_score, "max_risk": 12, "issues": issues}

    def _ip_network_score(self, raw_data):
        """
        维度4：IP/网络环境合规（0-10 风险分）
        政策依据：X Fraud Detection — 数据中心 IP 和频繁 IP 切换触发"非真实用户"模型
        """
        account_status = raw_data.get("account_status", {})
        risk_score = 0
        issues = []

        if isinstance(account_status, dict):
            ip_type = account_status.get("ip_type", "unknown")
            ip_switches_per_week = account_status.get("ip_switches_per_week", 0)
            is_tor = account_status.get("is_tor_ip", False)

            if ip_type == "datacenter":
                risk_score += 5
                issues.append("⚠️ 数据中心 IP（AWS/阿里云/腾讯云等），加 5 分风险")
            elif ip_type == "tor":
                risk_score += 5
                issues.append("⚠️ Tor/暗网 IP，加 5 分风险")
            elif ip_type == "residential":
                issues.append("✅ 住宅 IP（正常）")

            if ip_switches_per_week > 5:
                risk_score += 3
                issues.append(f"⚠️ 频繁切换 IP（{ip_switches_per_week} 个/周），加 3 分风险")

        risk_score = min(risk_score, 10)
        if not issues:
            issues.append("✅ IP 环境正常")
        return {"risk_score": risk_score, "max_risk": 10, "issues": issues}

    def _shadowban_score(self, raw_data):
        """
        维度5：Shadowban（隐限流）检测（0-10 风险分）
        政策依据：Shadowban 不通知用户——通过搜索可见性/回复深度/印象数判断
        """
        account_status = raw_data.get("account_status", {})
        risk_score = 0
        issues = []

        if isinstance(account_status, dict):
            if account_status.get("search_visibility", True) == False:
                risk_score += 6
                issues.append("⚠️ 搜索用户名无推文显示（Shadowban），加 6 分风险")

            reply_depth = account_status.get("reply_depth", 0)
            if reply_depth > 0 and reply_depth < 3:
                risk_score += 3
                issues.append(f"⚠️ 回复深度仅 {reply_depth} 层（正常>5 层），加 3 分风险")

            impression_drop = account_status.get("impression_drop_pct", 0)
            if impression_drop > 50:
                risk_score += 3
                issues.append(f"⚠️ 近期印象数骤降 {impression_drop}%，加 3 分风险")

            hashtag_visibility = account_status.get("hashtag_visibility", True)
            if hashtag_visibility == False:
                risk_score += 4
                issues.append("⚠️ 搜索特定标签无该账号推文，加 4 分风险")

        risk_score = min(risk_score, 10)
        if not issues:
            issues.append("✅ 无 Shadowban 迹象")
        return {"risk_score": risk_score, "max_risk": 10, "issues": issues}

    def _follow_ratio_score(self, raw_data):
        """
        维度6：关注/粉丝比与增长模式（0-8 风险分）
        政策依据：X 反 Spam — 关注轰炸和机器人粉丝触发"非真实互动"模型
        """
        profile = raw_data.get("profile", {})
        account_status = raw_data.get("account_status", {})
        risk_score = 0
        issues = []

        if isinstance(profile, dict) and profile:
            following_count = profile.get("following_count", 0)
            followers_count = profile.get("followers_count", 0)

            if followers_count > 0 and following_count / followers_count > 10:
                risk_score += 4
                issues.append(f"⚠️ 关注/粉丝比 {following_count}/{followers_count} = {following_count/followers_count:.1f}:1（>10:1），疑似关注轰炸，加 4 分风险")

        if isinstance(account_status, dict):
            bot_follower_pct = account_status.get("bot_follower_pct", 0)
            if bot_follower_pct > 30:
                risk_score += 3
                issues.append(f"⚠️ 粉丝中机器人占比 {bot_follower_pct}%（>30%），加 3 分风险")

            blocked_accounts_pct = account_status.get("blocked_following_pct", 0)
            if blocked_accounts_pct > 50:
                risk_score += 2
                issues.append(f"⚠️ 关注列表含 >50% 被封账号，加 2 分风险")

        risk_score = min(risk_score, 8)
        if not issues:
            issues.append("✅ 关注/粉丝比正常")
        return {"risk_score": risk_score, "max_risk": 8, "issues": issues}

    def _premium_score(self, raw_data):
        """
        维度7：Premium 会员等级（0-8 风险分，负分为信任加分）
        政策依据：Premium+ 提供验证蓝标和"真实用户"信任信号
        """
        account_status = raw_data.get("account_status", {})
        profile = raw_data.get("profile", {})
        risk_score = 0
        issues = []

        if isinstance(account_status, dict):
            premium_type = account_status.get("premium_type", "none")

            if premium_type == "none":
                # 未开通 Premium
                if isinstance(profile, dict) and profile.get("followers_count", 0) > 10000:
                    risk_score = 2
                    issues.append("⚠️ 粉丝>10K 但未开通 Premium，加 2 分风险")
                else:
                    issues.append("✅ 未开通 Premium（无加分）")
            elif premium_type == "basic":
                issues.append("✅ Premium Basic（$3/月）")
            elif premium_type == "premium":
                risk_score = -2  # 信任加分
                issues.append("✅ Premium（$8/月），-2 分信任加分")
            elif premium_type == "premium_plus":
                risk_score = -5  # 信任加分
                issues.append("✅ Premium+（$200/月，认证号），-5 分信任加分")

        return {"risk_score": risk_score, "max_risk": 8, "issues": issues, "premium_type": account_status.get("premium_type", "unknown") if isinstance(account_status, dict) else "unknown"}

    def _content_diversity_score(self, raw_data, historical_data):
        """
        维度8：内容多样性与活跃度（0-12 风险分）
        政策依据：X 算法偏好"真实互动"——纯搬运/无互动账号被降权
        """
        tweets = raw_data.get("recent_tweets", [])
        if not tweets:
            return {"risk_score": 0, "max_risk": 12, "issues": ["✅ 无推文，无多样性风险"]}

        adult_keywords = ["小穴", "肉棒", "鸡巴", "淫", "精液", "自慰", "高潮", "蜜穴", "屁穴",
            "男娘", "伪娘", "男の娘", "mtf", "ftm", "药娘", "cd", "crossdress",
            "femboy", "ts", "乳胶", "latex", "胶衣", "女仆", "假发", "cosplay",
            "nsfw", "18+", "adult", "涩涩", "调教", "拘束", "sm", "露出",
            "颜射", "足交", "手淫", "飞机杯", "吃药", "事后",
            "援交", "约炮", "yp", "插穴", "口交", "肛交", "阴道", "阴茎", "阴蒂", "大胸", "巨乳",
            "裸照", "果照", "走光", "姿势", "体位", "操", "干", "婊子", "骚", "操粉", "草粉", "上床"]

        risk_score = 0
        issues = []

        # A. 单一类型内容检测
        adult_count = sum(1 for t in tweets if isinstance(t, dict) and
                         any(kw in str(t.get("text", "")).lower() for kw in adult_keywords))
        adult_ratio = adult_count / len(tweets) if tweets else 0
        if adult_ratio > 0.8:
            risk_score += 5
            issues.append(f"⚠️ 单一 NSFW 内容占比 {adult_ratio:.0%}（>80%），加 5 分风险")

        # B. 原创与搬运比
        retweet_count = sum(1 for t in tweets if isinstance(t, dict) and t.get("is_retweet"))
        original_count = len(tweets) - retweet_count
        if original_count > 0 and retweet_count / original_count > 3:
            risk_score += 4
            issues.append(f"⚠️ 原创与搬运比 1:{retweet_count/original_count:.1f}（<1:3），加 4 分风险")
        elif original_count == 0 and len(tweets) > 5:
            risk_score += 4
            issues.append(f"⚠️ 全部为搬运内容（{len(tweets)} 条），加 4 分风险")

        # C. 发布时间集中检测
        import datetime
        dates = []
        for t in tweets:
            if isinstance(t, dict) and t.get("datetime"):
                try:
                    dt = datetime.datetime.fromisoformat(t["datetime"].replace("Z", "+00:00"))
                    dates.append(dt)
                except:
                    pass
        if len(dates) >= 5:
            dates.sort()
            two_hours = datetime.timedelta(hours=2)
            concentrated = sum(1 for d in dates if (dates[-1] - d) <= two_hours)
            if concentrated / len(dates) > 0.6:
                risk_score += 3
                issues.append(f"⚠️ {concentrated}/{len(dates)} 条推文在2小时内发布（>60%），加 3 分风险")

        # D. 无互动内容检测
        low_engagement = sum(1 for t in tweets if isinstance(t, dict) and t.get("likes", 0) < 5)
        if low_engagement / len(tweets) > 0.7:
            risk_score += 3
            issues.append(f"⚠️ {low_engagement}/{len(tweets)} 条推文互动低（<5赞），加 3 分风险")

        risk_score = min(risk_score, 12)
        if not issues:
            issues.append("✅ 内容多样性与活跃度正常")
        return {"risk_score": risk_score, "max_risk": 12, "issues": issues}
