import json
import os
import subprocess
import sys

# Define locations
work_dir = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
config_path = os.path.join(work_dir, "config.json")
python_exe = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"

# 1. Read existing config.json
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Save the original accounts list
original_accounts = config["accounts"] or []

# Find KkdTym, kaixintangtang, dangao0709 profiles to make sure we can restore properly later,
# but we can also just filter original_accounts to keep only dangao0709 and kaixintangtang if needed.
# Let's filter original_accounts for "dangao0709" and "kaixintangtang".
restored_accounts = [acc for acc in original_accounts if acc["username"] in ["dangao0709", "kaixintangtang"]]
# If any is missing, let's keep them anyway or construct them. We have them all.

# 9 target accounts
target_usernames = [
    "sunny31059", "sino11680908", "shutiaoniang", "jiajia2475", 
    "chichi_maddy", "VulpesM", "wuuuuuucy", "5277888MCHS", "urlittlecuteboy"
]

target_accounts = []
for name in target_usernames:
    target_accounts.append({
        "username": name,
        "display_name": name,
        "qq": "123456789",
        "email": "test@example.com"
    })

# 2. Modify config.json with target accounts
config["accounts"] = target_accounts
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print("Updated config.json with target accounts.")

# 3. Run monitor.py
print("Running monitor.py...")
proc = subprocess.run(
    [python_exe, "monitor.py"],
    cwd=work_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8'
)

print("STDOUT:")
print(proc.stdout)
print("STDERR:")
print(proc.stderr)

# 4. Restore config.json to containing dangao0709 and kaixintangtang
config["accounts"] = restored_accounts
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print("Restored config.json to target formal backup.")

# 5. Extract scores and generate summary
# Let's parse results from the stdout or the generated report/data.
# The data is saved under data/account_data/<username>/<date>.json or data/reports/
# Let's scan data_store.py or config output settings to find the daily files.
import datetime
today = datetime.date.today().isoformat()
summary_data = {}

for name in target_usernames:
    # check data/account_data/<name>/<today>.json
    json_file = os.path.join(work_dir, "data", "account_data", name, f"{today}.json")
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
                # Look at assessment or raw
                score = data.get("assessment", {}).get("score", "N/A")
                level = data.get("assessment", {}).get("level", "N/A")
                summary_data[name] = {"score": score, "level": level}
        except Exception as e:
            summary_data[name] = {"error": f"Failed to read: {e}"}
    else:
        summary_data[name] = {"error": "JSON file not found"}

print("\n--- Summary of Scores ---")
print(json.dumps(summary_data, indent=4, ensure_ascii=False))

# Also write to local data as requested
summary_out_path = os.path.join(work_dir, "data", "eval_summary_2026-07-25.json")
with open(summary_out_path, 'w', encoding='utf-8') as sf:
    json.dump(summary_data, sf, indent=4, ensure_ascii=False)
print(f"Summary written to: {summary_out_path}")
