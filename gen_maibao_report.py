#!/usr/bin/env python3
"""为 @Maibao1998 生成 HTML 可视化报告（复用 generate_reports.gen_report）。"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_reports import gen_report

WS = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(f'{WS}/data/maibao1998_risk_v3.json', encoding='utf-8'))
html = gen_report(data)
out = f'{WS}/maibao1998_rectification_v5.html'
open(out, 'w', encoding='utf-8').write(html)
print('Report written to', out, '| bytes:', len(html), '| score:', data['score'])
