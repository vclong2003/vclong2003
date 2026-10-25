from collections import Counter, defaultdict
from html import escape
import json
import os
import urllib.request

TOKEN = os.environ["METRICS_TOKEN"]
USER = os.environ["GH_USER"]
IGNORE = {"HTML", "CSS"}
TOP = 6

INCLUDE_ORGS = True  
INCLUDE_FORKS = (
    False  
)
INCLUDE_COLLAB = False  

affiliations = ["owner"]
if INCLUDE_ORGS:
    affiliations.append("organization_member")
if INCLUDE_COLLAB:
    affiliations.append("collaborator")
AFFILIATION_PARAM = ",".join(affiliations)

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
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Ruby": "#701516",
    "C++": "#f34b7d",
    "C": "#555555",
}
FALLBACK = "#8b949e"
OTHER_COLOR = "#6e7681"


def api(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def all_repos():
    page = 1
    while True:
        # visibility=all pulls BOTH public and private
        url = (
            f"https://api.github.com/user/repos"
            f"?visibility=all"
            f"&affiliation={AFFILIATION_PARAM}"
            f"&per_page=100&page={page}"
        )
        batch = api(url)
        if not batch:
            break

        for repo in batch:
            # Skip forks unless explicitly allowed (forks often pull huge vendor codebases)
            if repo.get("fork") and not INCLUDE_FORKS:
                continue
            yield repo["full_name"]

        page += 1


totals = Counter()
repos_using = defaultdict(set)
repo_count = 0

for name in all_repos():
    repo_count += 1
    try:
        lang_data = api(f"https://api.github.com/repos/{name}/languages")
        for lang, size in lang_data.items():
            if lang in IGNORE:
                continue
            totals[lang] += size
            repos_using[lang].add(name)
    except Exception:
        # Ignore repos where language stats fail to load or permissions are restricted
        continue

grand = sum(totals.values()) or 1
top = totals.most_common(TOP)
rest = grand - sum(n for _, n in top)

rows = [(lang, n) for lang, n in top]
if rest > 0:
    rows.append(("Other", rest))

# Layout Dimensions
CARD_WIDTH = 460
BAR_WIDTH = 400
BAR_X = 30
BAR_Y = 64
BAR_HEIGHT = 10
GRID_START_Y = 104
ROW_HEIGHT = 26

# Render Segmented Progress Bar
bar_segments = []
current_x = 0.0
for lang, n in rows:
    color = OTHER_COLOR if lang == "Other" else COLORS.get(lang, FALLBACK)
    w = (n / grand) * BAR_WIDTH
    bar_segments.append(
        f'<rect x="{current_x:.2f}" y="0" width="{w:.2f}" height="{BAR_HEIGHT}" fill="{color}"/>'
    )
    current_x += w

# Render Language Grid (2 Columns)
legend = []
COL_X = [30, 240]

for i, (lang, n) in enumerate(rows):
    col = i % 2
    row = i // 2
    x = COL_X[col]
    y = GRID_START_Y + (row * ROW_HEIGHT)

    color = OTHER_COLOR if lang == "Other" else COLORS.get(lang, FALLBACK)
    pct = (n / grand) * 100

    legend.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="4.5" fill="{color}"/>')
    legend.append(
        f'<text x="{x + 18}" y="{y}" class="lang-name">{escape(lang)}</text>'
    )
    legend.append(
        f'<text x="{x + 175}" y="{y}" class="lang-pct">{pct:.1f}%</text>'
    )

total_rows = (len(rows) + 1) // 2
card_height = GRID_START_Y + (total_rows * ROW_HEIGHT) + 18

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{card_height}" viewBox="0 0 {CARD_WIDTH} {card_height}">
  <style>
    :root {{
      --bg: #ffffff;
      --border: #d0d7de;
      --title: #1f2328;
      --sub: #656d76;
      --pct: #57606a;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0d1117;
        --border: #30363d;
        --title: #f0f6fc;
        --sub: #8b949e;
        --pct: #7d8590;
      }}
    }}
    .bg {{ fill: var(--bg); stroke: var(--border); stroke-width: 1px; rx: 8px; }}
    .title {{ font: 600 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--title); }}
    .sub {{ font: 400 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--sub); }}
    .lang-name {{ font: 500 12.5px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--title); }}
    .lang-pct {{ font: 400 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--pct); text-anchor: end; }}
  </style>

  <!-- Card Background -->
  <rect width="{CARD_WIDTH}" height="{card_height}" class="bg"/>

  <!-- Card Header -->
  <text x="30" y="32" class="title">Most Used Languages</text>
  <text x="30" y="48" class="sub">Across all {repo_count} repositories</text>

  <!-- Bar Track -->
  <defs>
    <clipPath id="bar-clip">
      <rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="5" ry="5"/>
    </clipPath>
  </defs>
  <g clip-path="url(#bar-clip)" transform="translate({BAR_X}, {BAR_Y})">
    {''.join(bar_segments)}
  </g>

  <!-- Languages 2-Column Grid -->
  {''.join(legend)}
</svg>
"""

with open("languages.svg", "w", encoding="utf-8") as f:
    f.write(svg)
