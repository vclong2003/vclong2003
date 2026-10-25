import os, json, urllib.request
from collections import Counter, defaultdict
from html import escape

TOKEN = os.environ["METRICS_TOKEN"]
USER = os.environ["GH_USER"]
IGNORE = {"HTML", "CSS"}
TOP = 8

# Fixed colors per language, so they never change when rankings shift
COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "Java": "#b07219",
    "C#": "#178600",
    "PHP": "#4F5D95",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
    "Objective-C": "#438eff",
    "Twig": "#c1d026",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Ruby": "#701516",
    "C++": "#f34b7d",
    "C": "#555555",
}
FALLBACK = "#999999"
OTHER_COLOR = "#cccccc"

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
    rows.append(("Other", rest, None))

WIDTH = 520
BAR_Y = 56
ROWS_Y = 100
ROW = 22

bar = []
x = 0.0
for lang, n, _ in rows:
    color = OTHER_COLOR if lang == "Other" else COLORS.get(lang, FALLBACK)
    w = WIDTH * n / grand
    bar.append(f'<rect x="{x:.2f}" y="{BAR_Y}" width="{w:.2f}" height="14" fill="{color}"/>')
    x += w

legend = []
for i, (lang, n, nrepos) in enumerate(rows):
    y = ROWS_Y + i * ROW
    color = OTHER_COLOR if lang == "Other" else COLORS.get(lang, FALLBACK)
    pct = 100 * n / grand
    repos_text = f"{nrepos} repos" if nrepos else ""
    legend.append(f'<rect x="10" y="{y - 9}" width="10" height="10" fill="{color}"/>')
    legend.append(f'<text x="28" y="{y}" class="t">{escape(lang)}</text>')
    legend.append(f'<text x="330" y="{y}" class="t" text-anchor="end">{pct:.1f}%</text>')
    legend.append(f'<text x="430" y="{y}" class="t" text-anchor="end">{n / 1024:,.0f} KB</text>')
    legend.append(f'<text x="510" y="{y}" class="t" text-anchor="end">{repos_text}</text>')

height = ROWS_Y + len(rows) * ROW + 10
summary = f"{repo_count} repos · {grand / 1024:,.0f} KB of code · {len(totals)} languages"

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH + 20}" height="{height}">'
    f'<style>.t{{font:13px Arial,sans-serif;fill:#000}}'
    f'.h{{font:bold 16px Arial,sans-serif;fill:#000}}'
    f'.s{{font:12px Arial,sans-serif;fill:#555}}</style>'
    f'<text x="10" y="24" class="h">Languages · {escape(USER)}</text>'
    f'<text x="10" y="42" class="s">{escape(summary)}</text>'
    + "".join(bar) + "".join(legend) +
    "</svg>"
)

with open("languages.svg", "w") as f:
    f.write(svg)
