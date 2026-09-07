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

# --- heatmap ---
CW, CH, GAP, PAD = 10, 10, 2, 16
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
        cells.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'
                     % (x, y, CW, CH, color(d['contributionCount'])))
total = sum(d['contributionCount'] for d in days)
heat = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        '<g>%s</g><text x="%d" y="%d" fill="#8b949e" font-size="12" font-family="Segoe UI, sans-serif">%d contributions in the last year</text></svg>'
        % (w, h, w, h, ''.join(cells), PAD, h - 2, total))

# --- weekly area line ---
LW, LH = 900, 220
m = 10
per_date = {d['date']: d['contributionCount'] for d in days}
series = []
cur = date.fromisoformat(days[0]['date'])
end = date.fromisoformat(days[-1]['date'])
while cur <= end:
    series.append(per_date.get(cur.isoformat(), 0))
    cur += timedelta(days=1)
weekly = [sum(series[i:i + 7]) for i in range(0, len(series), 7)]
peak = max(weekly) or 1
pw = (LW - m * 2) / max(len(weekly) - 1, 1)
pts = [('%.1f' % (m + i * pw), '%.1f' % (LH - m - v / peak * (LH - m * 2))) for i, v in enumerate(weekly)]
area_svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#26a641" stop-opacity="0.9"/>'
    '<stop offset="1" stop-color="#2aa8c0" stop-opacity="0.05"/>'
    '</linearGradient></defs>'
    '<polygon points="%s,%s %s %s,%s" fill="url(#g)"/>'
    '<polyline points="%s" fill="none" stroke="#2aa885" stroke-width="2"/></svg>'
    % (LW, LH, m, LH - m, ' '.join('%s,%s' % p for p in pts), LW - m, LH - m,
       ' '.join('%s,%s' % p for p in pts))
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
