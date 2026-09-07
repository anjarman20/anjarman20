import json
import urllib.request
import os
import re
import time
from datetime import date, timedelta

USER = 'anjarman20'
README_PATH = 'README.md'
MARK_START = '<!-- activity-graph:start -->'
MARK_END = '<!-- activity-graph:end -->'
WEEKS = 52

query = {'query': '{ user(login: "%s") { contributionsCollection { contributionCalendar { weeks { contributionDays { contributionCount date } } } } } }' % USER}
req = urllib.request.Request(
    'https://api.github.com/graphql',
    data=json.dumps(query).encode(),
    headers={
        'Authorization': 'bearer ' + os.environ['GITHUB_TOKEN'],
        'Content-Type': 'application/json',
        'User-Agent': 'activity-graph',
    },
)
with urllib.request.urlopen(req) as resp:
    cal = json.load(resp)['data']['user']['contributionsCollection']['contributionCalendar']

days = [d for w in cal['weeks'] for d in w['contributionDays']]
days = days[-WEEKS * 7:]

sorted_counts = sorted(d['contributionCount'] for d in days)
max_c = max(sorted_counts[int(len(sorted_counts) * 0.97)], 1)

def color(c):
    if c <= 0:
        return '#161b22'
    t = min(c / max_c, 1.0)
    return '#%02x%02x%02x' % (int(8 + t * 22), int(48 + t * 151), int(56 + t * 199))

# --- heatmap with per-day tooltips (inline in README -> <title> works on hover) ---
CW, CH, GAP, PAD = 11, 11, 2, 4
n_weeks = min(WEEKS, len(cal['weeks']))
w = PAD * 2 + n_weeks * (CW + GAP)
h = PAD * 2 + 7 * (CH + GAP)
cells = []
for wi, wk in enumerate(cal['weeks'][-n_weeks:]):
    x = PAD + wi * (CW + GAP)
    for d in wk['contributionDays']:
        if not d['date']:
            continue
        y = PAD + date.fromisoformat(d['date']).weekday() * (CH + GAP)
        c = d['contributionCount']
        label = '%d contribution%s on %s' % (c, 's' if c != 1 else '', d['date'])
        cells.append('<rect x="%d" y="%s" width="%d" height="%d" rx="2" fill="%s"><title>%s</title></rect>'
                     % (x, y, CW, CH, color(c), label))
# total label
total = sum(d['contributionCount'] for d in days)
legend = ('<text x="%d" y="%d" fill="#8b949e" font-size="12" font-family="Segoe UI, sans-serif">%d contributions in the last year</text>'
          % (PAD, h - 2, total))
heat = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        '<g>%s</g>%s</svg>' % (w, h + 16, w, h + 16, ''.join(cells), legend))

# --- weekly area line with per-week tooltips ---
LW, LH = w, 180
m = 10
per_date = {d['date']: d['contributionCount'] for d in days}
series = []
cur = date.fromisoformat(days[0]['date'])
end = date.fromisoformat(days[-1]['date'])
while cur <= end:
    series.append((cur, per_date.get(cur.isoformat(), 0)))
    cur += timedelta(days=1)
weekly = [sum(v for _, v in series[i:i + 7]) for i in range(0, len(series), 7)]
peak = max(weekly) or 1
pw = (LW - m * 2) / max(len(weekly) - 1, 1)
pts = [('%f' % (m + i * pw), '%f' % (LH - m - v / peak * (LH - m * 2))) for i, v in enumerate(weekly)]
# invisible hover columns over each week
hover = []
for i, v in enumerate(weekly):
    x0 = m + max(i * pw - pw / 2, 0)
    x1 = m + min((i + 1) * pw + pw / 2, LW - m)
    start_i = min(i * 7, len(series) - 1)
    d0 = series[start_i][0].isoformat()
    d1 = series[min(i * 7 + 6, len(series) - 1)][0].isoformat()
    hover.append('<rect x="%f" y="0" width="%f" height="%d" fill="transparent"><title>%d turns: %d contributions (%s to %s)</title></rect>'
                 % (x0, x1 - x0, LH, i + 1, v, d0, d1))
area_svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#26a641" stop-opacity="0.9"/>'
    '<stop offset="1" stop-color="#2aa8c0" stop-opacity="0.05"/>'
    '</linearGradient></defs>'
    '<polygon points="%s %s %s" fill="url(#g)"/>'
    '<polyline points="%s" fill="none" stroke="#2aa885" stroke-width="2"/>'
    '<g>%s</g></svg>'
    % (LW, LH, '%f,%f ' % (m, LH - m), ' '.join('%s,%s' % p for p in pts), '%f,%f' % (LW - m, LH - m),
       ' '.join('%s,%s' % p for p in pts), ''.join(hover))
)

block = '%s\n<div align="center">\n%s\n%s\n</div>\n%s' % (MARK_START, area_svg, heat, MARK_END)

with open(README_PATH) as f:
    readme = f.read()
if MARK_START in readme:
    readme = re.sub(re.escape(MARK_START) + '.*?' + re.escape(MARK_END), lambda m: block, readme, flags=re.S)
else:
    # replace old <img> block (lines 71-73 area)
    readme = re.sub(r'<p align="center">\n\s*<img src="assets/activity-graph.*?</p>\n', lambda m: block + '\n', readme, flags=re.S)
with open(README_PATH, 'w') as f:
    f.write(readme)

print('inline svg written | total:', total)
