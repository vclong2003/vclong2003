import os, json, urllib.request
from collections import Counter

TOKEN = os.environ["METRICS_TOKEN"]
USER = os.environ["GH_USER"]
IGNORE = {"HTML", "CSS"}
PALETTE = ["#f1e05a", "#3178c6", "#e34c26", "#b07219", "#4F5D95",
           "#6e40c9", "#89e051", "#178600", "#dea584", "#555555"]

def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def owned_repos():
    page = 1
    while True:
        batch = api(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}")
        if not batch:
            break
        for repo in batch:
            if not repo["fork"]:
                yield repo["full_name"]
        page += 1

totals = Counter()
for name in owned_repos():
    for lang, size in api(f"https://api.github.com/repos/{name}/languages").items():
        if lang not in IGNORE:
            totals[lang] += size

top = totals.most_common(8)
total = sum(n for _, n in top) or 1
width = 600
x = 0.0
bar, legend = [], []
for i, (lang, n) in enumerate(top):
    color = PALETTE[i % len(PALETTE)]
    w = width * n / total
    bar.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="14" fill="{color}"/>')
    x += w
    y = 40 + i * 20
    legend.append(f'<circle cx="8" cy="{y}" r="5" fill="{color}"/>'
                  f'<text x="20" y="{y + 4}" font-family="Arial" font-size="13" fill="#000">'
                  f'{lang} {100 * n / total:.1f}%</text>')

height = 50 + len(top) * 20
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
       + "".join(bar) + "".join(legend) + "</svg>")
with open("languages.svg", "w") as f:
    f.write(svg)
