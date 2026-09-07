import json
import urllib.request
from datetime import date, timedelta

USER = 'anjarman20'
OUT = 'assets/activity-graph.svg'
WEEKS = 52

# fetch contribution calendar (public API, unauthenticated quota: 60/h, ~1 call/day is fine)
query = {'query': '{ user(login: "%s") { contributionsCollection { contributionCalendar { weeks { contributionDays { contributionCount date } } } } } }' % USER}
req = urllib.request.Request(
    'https://api.github.com/graphql',
    data=json.dumps(query).encode(),
    headers={
        'Authorization': 'bearer ' + __import__('os').environ['GITHUB_TOKEN'],
        'Content-Type': 'application/json',
        'User-Agent': 'activity-graph',
    },
)
with urllib.request.urlopen(req) as resp:
    data = json.load(resp)['data']['user']['contributionsCollection']['contributionCalendar']

days = [d for w in data['weeks'] for d in w['contributionDays']]
days = days[-WEEKS * 7:]  # last 52 full weeks

# smooth max so a single 40-commit day doesn't flatten everything
sorted_counts = sorted(d['contributionCount'] for d in days)
max_c = max(sorted_counts[int(len(sorted_counts) * 0.97)], 1)

def color(c):
    if c <= 0:
        return '#161b22'
    t = min(c / max_c, 1.0)
    # react-dark style: near-black -> teal
    r = int(8 + t * 22)
    g = int(48 + t * 151)
    b = int(56 + t * 199)
    return '#%02x%02x%02x' % (r, g, b)

# daily totals for area line
dates = [d['date'] for d in days]
start = date.fromisoformat(dates[0])
end = date.fromisoformat(dates[-1])
per_day = {d['date']: d['contributionCount'] for d in days}
series = []
cur = start
while cur <= end:
    series.append(per_day.get(cur.isoformat(), 0))
    cur += timedelta(days=1)

# --- heatmap svg ---
CW, CH, GAP, PAD = 10, 10, 2, 16
w = PAD * 2 + WEEKS * (CW + GAP)
h = PAD * 2 + 7 * (CH + GAP)
cells = []
x = PAD
week_i = 0
for wk in data['weeks']:
    if week_i >= WEEKS:
        break
    for d in wk['contributionDays']:
        if not d['date']:
            continue
        y = PAD + date.fromisoformat(d['date']).weekday() * (CH + GAP)
        cells.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>' % (x, y, CW, CH, color(d['contributionCount'])))
    x += CW + GAP
    week_i += 1

heat = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
    '<g>%s</g></svg>' % (w, h, w, h, ''.join(cells))
)

# --- area line svg --- (react-dark look: line + gradient fill)
LW, LH = 900, 220
m = 10
total = max(sum(series[i:i+7]) for i in range(0, len(series), 7)) or 1
weekly = [sum(series[i:i+7]) for i in range(0, len(series), 7)]
pw = (LW - m * 2) / max(len(weekly) - 1, 1)
pts = []
for i, v in enumerate(weekly):
    pts.append((m + i * pw, LH - m - (v / max(total, 1)) * (LH - m * 2)))
area = '%f,%f ' % (m, LH - m) + ' '.join('%f,%f' % (px, py) for px, py in pts) + ' %f,%f' % (LW - m, LH - m)
line = ' '.join('%f,%f' % (px, py) for px, py in pts)
area_svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#26a641" stop-opacity="0.9"/>'
    '<stop offset="0.5" stop-color="#2aa885" stop-opacity="0.4"/>'
    '<stop offset="1" stop-color="#2aa8c0" stop-opacity="0.05"/>'
    '</linearGradient></defs>'
    '<polygon id="area" points="%s" fill="url(#g)"/>'
    '<polyline id="line" points="%s" fill="none" stroke="#2aa885" stroke-width="2"/>'
    '</svg>' % (LW, LH, area, line)
)

import os
os.makedirs('assets', exist_ok=True)

# cache-bust README <img> so GitHub Camo serves the new SVG
readme_path = 'README.md'
with open(readme_path) as f:
    readme = f.read()
for name in ('activity-graph', 'activity-graph-heatmap'):
    import re
    readme = re.sub(
        r'(assets/%s\.svg\?v=)\d+' % name,
        r'\g<1>%d' % __import__('time').time_ns(),
        readme,
    )
with open(readme_path, 'w') as f:
    f.write(readme)
with open(OUT, 'w') as f:
    f.write(area_svg)
with open(OUT.replace('.svg', '-heatmap.svg'), 'w') as f:
    f.write(heat)
print('total contributions (last %d weeks): %d' % (WEEKS, sum(series)))
