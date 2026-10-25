import os, json, urllib.request
from collections import Counter, defaultdict
from html import escape

TOKEN = os.environ["METRICS_TOKEN"]
USER = os.environ["GH_USER"]
IGNORE = {"HTML", "CSS"}
TOP = 8

# Fixed colors by language name
COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "Java": "#b07219",
    "Kotlin": "#A97BFF",
    "C#": "#178600",
    "PHP": "#4F5D95",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
    "Objective-C": "#438eff",
    "Twig": "#c1d026",
    "Swift": "#F05138",
    "Ruby": "#701516",
    "C++": "#f34b7d",
    "C": "#555555",
}
FALLBACK = "#999999"
OTHER = "#cccccc"

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
repos_using = defaultdict(set)
repo_count = 0

for name in owned_repos():
    repo_count += 1
    for lang, size in api(f"https://api.github.com/repos/{name}/languages").items():
        if lang in IGNORE:
            continue
        totals[lang] += size
        repos_using[lang].add(name)

grand = sum(totals.values()) or 1
top = totals.most_common(TOP)
rest = grand - sum(n for _, n in top)

rows = [(lang, n, len(repos_using[lang])) for lang, n in top]
if rest > 0:
    rows.append(("Other", rest, 0))

def color(lang):
    if lang == "Other":
        return OTHER
    return COLORS.get(lang, FALLBACK)

WIDTH = 360
BAR_Y = 34
BAR_H = 8
ROW_Y = 62
ROW = 16

bar, legend = [], []
x = 0.0
for lang, n, _ in rows:
    w = WIDTH * n / grand
    bar.append(f'<rect x="{x:.2f}" y="{BAR_Y}" width="{w:.2f}" height="{BAR_H}" fill="{color(lang)}"/>')
    x += w

for i, (lang, n, nrepos) in enumerate(rows):
    y = ROW_Y + i * ROW
    pct = 100 * n / grand
    repos_text = f"{nrepos} repos" if nrepos else ""
    legend.append(f'<circle cx="14" cy="{y - 4}" r="4" fill="{color(lang)}"/>')
    legend.append(f'<text x="26" y="{y}" class="t">{escape(lang)}</text>')
    legend.append(f'<text x="220" y="{y}" class="t" text-anchor="end">{pct:.1f}%</text>')
    legend.append(f'<text x="290" y="{y}" class="t" text-anchor="end">{n / 1024:,.0f} KB</text>')
    legend.append(f'<text x="370" y="{y}" class="m" text-anchor="end">{repos_text}</text>')

height = ROW_Y + len(rows) * ROW + 6
summary = f"{repo_count} repos · {grand / 1024:,.0f} KB · {len(totals)} languages"

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="380" height="{height}">'
    f'<style>'
    f'.h{{font:600 13px Arial,sans-serif;fill:#111}}'
    f'.m{{font:11px Arial,sans-serif;fill:#666}}'
    f'.t{{font:11px Arial,sans-serif;fill:#222}}'
    f'</style>'
    f'<text x="10" y="16" class="h">Languages</text>'
    f'<text x="10" y="28" class="m">{escape(summary)}</text>'
    + "".join(bar) + "".join(legend) +
    "</svg>"
)

with open("languages.svg", "w") as f:
    f.write(svg)
