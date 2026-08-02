#!/usr/bin/env python3
"""从 HTML 文件中提取推文 meta 标签"""
import re
import json

html = open('debug_sunny_full.html', encoding='utf-8').read()

# 找 articleBody
pattern1 = r'itemprop=["\x27]articleBody["\x27][^>]*content=["\x27]([^"\x27]{10,500})["\x27]'
matches1 = re.findall(pattern1, html)
print('找到 articleBody:', len(matches1))
for m in matches1[:5]:
    print('  ', m[:200])

# 找 text
pattern2 = r'itemprop=["\x27]text["\x27][^>]*content=["\x27]([^"\x27]{10,500})["\x27]'
matches2 = re.findall(pattern2, html)
print('找到 text:', len(matches2))
for m in matches2[:5]:
    print('  ', m[:200])

# 找 headline
pattern3 = r'itemprop=["\x27]headline["\x27][^>]*content=["\x27]([^"\x27]{10,500})["\x27]'
matches3 = re.findall(pattern3, html)
print('找到 headline:', len(matches3))
for m in matches3[:5]:
    print('  ', m[:200])
