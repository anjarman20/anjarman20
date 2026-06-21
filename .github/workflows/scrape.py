import re
import json
import urllib.request

url = 'https://discord.com/servers/arqonara-com-1093899694121418802'
req = urllib.request.Request(
    url,
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
)

with urllib.request.urlopen(req) as resp:
    html = resp.read().decode()

members_match = re.search(r'([\d,]+)\s*Members', html)
online_match = re.search(r'([\d,]+)\s*Online', html)

data = {
    'members': members_match.group(1).replace(',', '') if members_match else '7168',
    'online': online_match.group(1) if online_match else '0',
}

with open('community-stats.json', 'w') as f:
    json.dump(data, f)

print('Members:', data['members'], '| Online:', data['online'])
