from collections import Counter, defaultdict
from html import escape
import json
import os
import urllib.request

TOKEN = os.environ["METRICS_TOKEN"]
USER = os.environ["GH_USER"]
IGNORE = {"HTML", "CSS"}
TOP = 8 

INCLUDE_ORGS = True
INCLUDE_FORKS = False
INCLUDE_COLLAB = False

affiliations = ["owner"]
if INCLUDE_ORGS:
    affiliations.append("organization_member")
if INCLUDE_COLLAB:
    affiliations.append("collaborator")
AFFILIATION_PARAM = ",".join(affiliations)

COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "Java": "#b07219",
    "Kotlin": "#A97BFF",
    "C#": "#178600",
    "PHP": "#4F5D95",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
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
        continue

grand = sum(totals.values()) or 1
top = totals.most_common(TOP)
rest = grand - sum(n for _, n in top)

rows = [(lang, n) for lang, n in top]
if rest > 0:
    rows.append(("Other", rest))

# --- Compact Layout Dimensions ---
CARD_WIDTH = 420
PADDING_X = 24
BAR_WIDTH = CARD_WIDTH - (PADDING_X * 2)  # 372px
BAR_X = PADDING_X
BAR_Y = 54
BAR_HEIGHT = 8
BAR_RADIUS = 4
GRID_START_Y = 82
ROW_HEIGHT = 22

# Render Bar Segments
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
COL_X = [24, 218]  # Balanced two columns

for i, (lang, n) in enumerate(rows):
    col = i % 2
    row = i // 2
    x = COL_X[col]
    y = GRID_START_Y + (row * ROW_HEIGHT)

    color = OTHER_COLOR if lang == "Other" else COLORS.get(lang, FALLBACK)
    pct = (n / grand) * 100

    # Compact 4px radius dot aligned to 12px text baseline
    legend.append(f'<circle cx="{x + 4}" cy="{y - 4}" r="4" fill="{color}"/>')
    legend.append(
        f'<text x="{x + 16}" y="{y}" class="lang-name">{escape(lang)}</text>'
    )
    legend.append(
        f'<text x="{x + 172}" y="{y}" class="lang-pct">{pct:.1f}%</text>'
    )

total_rows = (len(rows) + 1) // 2
card_height = GRID_START_Y + (total_rows * ROW_HEIGHT) + 6

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{card_height}" viewBox="0 0 {CARD_WIDTH} {card_height}">
  <style>
    :root {{
      --bg: #ffffff;
      --border: #d0d7de;
      --track: #ebedf0;
      --title: #1f2328;
      --sub: #656d76;
      --pct: #656d76;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0d1117;
        --border: #30363d;
        --track: #21262d;
        --title: #f0f6fc;
        --sub: #8b949e;
        --pct: #8b949e;
      }}
    }}
    .bg {{ fill: var(--bg); stroke: var(--border); stroke-width: 1px; rx: 6px; }}
    .title {{ font: 600 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--title); }}
    .sub {{ font: 400 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--sub); }}
    .lang-name {{ font: 500 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--title); }}
    .lang-pct {{ font: 400 11.5px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: var(--pct); text-anchor: end; }}
  </style>

  <!-- Card Background -->
  <rect width="{CARD_WIDTH}" height="{card_height}" class="bg"/>

  <!-- Card Header -->
  <text x="{PADDING_X}" y="26" class="title">Most Used Languages</text>
  <text x="{PADDING_X}" y="40" class="sub">Across all {repo_count} repositories</text>

  <!-- Progress Bar -->
  <defs>
    <clipPath id="bar-clip">
      <rect x="0" y="0" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="{BAR_RADIUS}" ry="{BAR_RADIUS}"/>
    </clipPath>
  </defs>

  <!-- Bar Track + Segments -->
  <g transform="translate({BAR_X}, {BAR_Y})">
    <rect width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="{BAR_RADIUS}" fill="var(--track)"/>
    <g clip-path="url(#bar-clip)">
      {''.join(bar_segments)}
    </g>
  </g>

  <!-- Language Grid -->
  {''.join(legend)}
</svg>
"""

with open("languages.svg", "w", encoding="utf-8") as f:
    f.write(svg)
