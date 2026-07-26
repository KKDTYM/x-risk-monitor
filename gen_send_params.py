import sys, json, base64, hashlib, re

BASE = "F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14"
ALIAS_ID = "alias_3lIggJS6kEo7vNtlVS_zTvfvF9B5xjs"  # bobi_wu@foxmail.com (primary)

# handle, recipient_email, recipient_name, html_file, out_json, [token]
handle      = sys.argv[1]
email       = sys.argv[2]
name        = sys.argv[3]
html_file   = sys.argv[4]
out_json    = sys.argv[5]
token       = sys.argv[6] if len(sys.argv) > 6 else None

path = f"{BASE}/{html_file}"
data = open(path, "rb").read()
b64   = base64.b64encode(data).decode()
sha1  = hashlib.sha1(data).hexdigest()
size  = len(data)

# extract total score
m = re.search(r'class="score-number">(\d+)', data.decode("utf-8", "ignore"))
score = int(m.group(1)) if m else None

def risk_level(s):
    if s is None: return "未知"
    if s >= 60: return "高风险"
    if s >= 30: return "中等风险"
    return "低风险"

level = risk_level(score)
score_txt = f"{score}/100" if score is not None else "（见附件）"

today = "2026-07-25"
subject = f"@{handle} X账号风险评估报告 v5（{today}）"

body = (
    f"您好，\n\n"
    f"附件是您 X 账号（@{handle}）的最新一期风险评估报告（v5，{today}）。\n\n"
    f"综合风险分：{score_txt}（{level}）\n\n"
    f"报告内含 6 个维度的详细评分、命中的风险项说明，以及对应的整改建议，"
    f"请在浏览器中打开 HTML 附件查看完整内容。\n\n"
    f"如有疑问或需要补充说明，可直接回复本邮件。\n\n"
    f"—— X账号风险监控系统"
)

params = {
    "alias_id": ALIAS_ID,
    "to": [{"email": email, "name": name}],
    "subject": subject,
    "body": body,
    "body_format": "PLAIN",
    "attachments": [{
        "filename": html_file,
        "content_type": "text/html",
        "content": b64,
        "size": size,
        "sha1": sha1,
    }],
}
if token:
    params["confirmation_token"] = token

# nested form expected by connector-proxy: {arguments: {...}}
nested = {"arguments": params}

with open(f"{BASE}/{out_json}", "w", encoding="utf-8") as f:
    json.dump(nested, f, ensure_ascii=False, indent=2)

# also echo a compact version for the tool call
print(json.dumps(nested, ensure_ascii=False))
print(f"\n# handle={handle} size={size} sha1={sha1} score={score} level={level}", file=sys.stderr)
