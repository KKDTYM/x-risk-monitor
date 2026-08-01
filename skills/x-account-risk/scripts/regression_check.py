#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归测试：对比当前评估结果与 golden_set 基线，漂移 >3 分告警。
用法: python regression_check.py [workspace_dir]
"""
import json
import os
import sys

WS = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
DATA = os.path.join(WS, "data")
golden_path = os.path.join(DATA, "golden_set.json")
if not os.path.exists(golden_path):
    print("NO GOLDEN SET — 先运行 assess 后生成 golden_set.json")
    sys.exit(1)

golden = json.load(open(golden_path, encoding="utf-8"))
engine = golden.get("engine", "?")
print(f"Golden 基线引擎: {engine} | 生成时间: {golden.get('generated_at')}")
print(f"{'账号':<22}{'基线':>6}{'当前':>6}{'漂移':>7}  状态")

fail = 0
for handle, g in sorted(golden["accounts"].items()):
    p = os.path.join(DATA, handle.lower() + "_risk.json")
    if not os.path.exists(p):
        print(f"{handle:<22}{g['score']:>6}{'缺失':>6}{'':>7}  ❌ 文件缺失")
        fail += 1
        continue
    cur = json.load(open(p, encoding="utf-8"))
    delta = cur["score"] - g["score"]
    status = "✅" if abs(delta) <= 3 else "⚠️ 漂移"
    if abs(delta) > 3:
        fail += 1
    print(f"{handle:<22}{g['score']:>6}{cur['score']:>6}{delta:>+7}  {status}")

print(f"\n结果: {'❌ 有 ' + str(fail) + ' 个漂移' if fail else '✅ 全部在 ±3 分以内'}")
sys.exit(1 if fail else 0)
