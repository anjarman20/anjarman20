import json
import urllib.request
import os
import re
import hashlib
import time
from datetime import date, timedelta

USER = 'anjarman20'
README_PATH = 'README.md'
HASH_PATH = '.github/workflows/.graph-hash'
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

# --- heatmap (with month/weekday labels + intensity legend) ---
CW, CH, GAP, PAD, LEFT = 10, 10, 2, 16, 26
n_weeks = min(WEEKS, len(cal['weeks']))
w = LEFT + n_weeks * (CW + GAP)
h = PAD + 7 * (CH + GAP) + 22
cells = []
months_done = set()
month_labels = []
for wi, wk in enumerate(cal['weeks'][-n_weeks:]):
    x = LEFT + wi * (CW + GAP)
    if wk['contributionDays'] and wk['contributionDays'][-1]['date']:
        mn = date.fromisoformat(wk['contributionDays'][-1]['date']).strftime('%b')
        if mn not in months_done:
            months_done.add(mn)
            month_labels.append('<text x="%d" y="11" fill="#8b949e" font-size="10" font-family="Segoe UI, sans-serif">%s</text>' % (x, mn))
    for d in wk['contributionDays']:
        if not d['date']:
            continue
        y = PAD + date.fromisoformat(d['date']).weekday() * (CH + GAP)
        cells.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'
                     % (x, y, CW, CH, color(d['contributionCount'])))
wd_labels = ['Mon', 'Wed', 'Fri']
wd_v = [0, 2, 4]
weekday = ''.join('<text x="2" y="%d" fill="#8b949e" font-size="9" font-family="Segoe UI, sans-serif">%s</text>'
                  % (PAD + vv * (CH + GAP) + 8, ww) for vv, ww in zip(wd_v, wd_labels))
swatches = ' '.join('<rect x="%.0f" y="%d" width="9" height="9" rx="2" fill="%s"/>'
                    % (w - 4 * 14 - i * 14, h - 10, color(cc))
                    for i, cc in enumerate([0, max_c // 3, int(max_c * 0.66), max_c]))
legend = ('<text x="%d" y="%d" fill="#8b949e" font-size="10" font-family="Segoe UI, sans-serif">Less %s More</text>'
          % (w - 4 * 14 - 34, h - 2, swatches))
total = sum(d['contributionCount'] for d in days)
cap = '<text x="0" y="%d" fill="#8b949e" font-size="10" font-family="Segoe UI, sans-serif">%d commits/yr</text>' % (h - 2, total)
heat = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        '<g>%s</g>%s%s%s%s</svg>'
        % (w, h, w, h, ''.join(cells), weekday, ''.join(month_labels), legend, cap))

# --- weekly area line (with axes) ---
LW, LH = 900, 240
LEFT, m = 44, 8
per_date = {d['date']: d['contributionCount'] for d in days}
series = []
cur = date.fromisoformat(days[0]['date'])
end = date.fromisoformat(days[-1]['date'])
while cur <= end:
    series.append(per_date.get(cur.isoformat(), 0))
    cur += timedelta(days=1)
weekly = [sum(series[i:i + 7]) for i in range(0, len(series), 7)]
peak = max(weekly) or 1
step = next((s for s in [10, 20, 25, 50, 100, 200, 250, 500, 1000] if peak <= s * 3), 1000)
y_top = (peak // step + 1) * step
X0, Y0, X1, Y1 = LEFT, 20, LW - 16, LH - 34
pw = (X1 - X0) / max(len(weekly) - 1, 1)
pts = [('%.1f' % (X0 + i * pw), '%.1f' % (Y1 - v / y_top * (Y1 - Y0))) for i, v in enumerate(weekly)]
grid = ''
for k in range(0, y_top + 1, step):
    y = Y1 - k / y_top * (Y1 - Y0)
    grid += '<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="#30363d"/><text x="%d" y="%.0f" fill="#8b949e" font-size="10" text-anchor="end" font-family="Segoe UI, sans-serif">%s</text>' % (X0, y, X1, y, X0 - 5, y + 3, f'{k}')
    if k: pass
# month ticks
months_done = set()
ticks = ''
for i, wk in enumerate(cal['weeks'][-WEEKS:]):
    if wk['contributionDays'] and wk['contributionDays'][-1]['date']:
        mn = date.fromisoformat(wk['contributionDays'][-1]['date']).strftime('%b')
        if mn not in months_done:
            months_done.add(mn)
            ticks += '<text x="%.1f" y="%d" fill="#8b949e" font-size="10" text-anchor="middle" font-family="Segoe UI, sans-serif">%s</text>' % (X0 + i * pw, LH - 8, mn)
area_svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#26a641" stop-opacity="0.9"/>'
    '<stop offset="1" stop-color="#2aa8c0" stop-opacity="0.05"/>'
    '</linearGradient></defs>%s'
    '<polygon points="%s,%s %s %s,%s" fill="url(#g)"/>'
    '<polyline points="%s" fill="none" stroke="#2aa885" stroke-width="2"/>%s</svg>'
    % (LW, LH, LW, LH, grid, X0, Y0, ' '.join('%s,%s' % p for p in pts), X1, Y1,
       ' '.join('%s,%s' % p for p in pts), ticks)
)

os.makedirs('assets', exist_ok=True)
with open('assets/activity-graph.svg', 'w') as f:
    f.write(area_svg)
with open('assets/activity-graph-heatmap.svg', 'w') as f:
    f.write(heat)

digest = hashlib.sha256((area_svg + heat).encode()).hexdigest()
if os.path.exists(HASH_PATH):
    with open(HASH_PATH) as f:
        old = f.read().strip()
else:
    old = ''
if digest == old:
    print('unchanged | total:', total)
else:
    ts = int(time.time())
    with open(README_PATH) as f:
        readme = f.read()
    readme = re.sub(r'(assets/activity-graph(?:-heatmap)?\.svg\?v=)\d+', r'\g<1>%d' % ts, readme)
    with open(README_PATH, 'w') as f:
        f.write(readme)
    with open(HASH_PATH, 'w') as f:
        f.write(digest)
    print('updated readme cache-bust | total:', total)
