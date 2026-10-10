"""Render a GitHub contribution streak card (light + dark SVG) from the GraphQL API."""

import datetime as dt
import json
import os
import sys
import urllib.request

LOGIN = os.environ.get("GITHUB_USER", "AkiCagkan")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "dist"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""

THEMES = {
    "streak": {  # light
        "bg": "#FFFFFF", "border": "#D0D7DE", "divider": "#D0D7DE",
        "text": "#1F2328", "muted": "#656D76", "accent": "#0969DA", "fire": "#BC4C00",
    },
    "streak-dark": {
        "bg": "#0D1117", "border": "#30363D", "divider": "#30363D",
        "text": "#E6EDF3", "muted": "#8B949E", "accent": "#58A6FF", "fire": "#F0883E",
    },
}

FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
FIRE = ("M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36"
        "C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67z"
        "M11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 "
        "4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z")


def graphql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_days():
    now = dt.datetime.now(dt.timezone.utc)
    first = graphql({"login": LOGIN, "from": iso(now - dt.timedelta(days=1)), "to": iso(now)})
    created = dt.datetime.fromisoformat(first["createdAt"].replace("Z", "+00:00"))

    days = {}
    for year in range(created.year, now.year + 1):
        start = max(created, dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc))
        end = min(now, dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        user = graphql({"login": LOGIN, "from": iso(start), "to": iso(end)})
        for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[dt.date.fromisoformat(day["date"])] = day["contributionCount"]
    return dict(sorted(days.items()))


def stats(days):
    dates = list(days)
    today = dates[-1]
    total = sum(days.values())
    first = next((d for d in dates if days[d]), today)

    longest = (0, today, today)
    run_len, run_start = 0, None
    for d in dates:
        if days[d]:
            if run_len == 0:
                run_start = d
            run_len += 1
            if run_len > longest[0]:
                longest = (run_len, run_start, d)
        else:
            run_len = 0

    # Today without contributions doesn't break the streak yet.
    end = today if days[today] else today - dt.timedelta(days=1)
    cur, d = 0, end
    while days.get(d):
        cur += 1
        d -= dt.timedelta(days=1)
    current = (cur, d + dt.timedelta(days=1), end) if cur else (0, today, today)
    return total, first, current, longest, today


def fmt(d, today):
    return f"{d:%b} {d.day}" if d.year == today.year else f"{d:%b} {d.day}, {d.year}"


def fmt_range(start, end, today):
    if start == end:
        return fmt(start, today)
    return f"{fmt(start, today)} - {fmt(end, today)}"


def text(x, y, value, color, size, weight=400, extra=""):
    return (f"<text x='{x}' y='{y}' text-anchor='middle' fill='{color}' font-family=\"{FONT}\" "
            f"font-weight='{weight}' font-size='{size}px' {extra}>{value}</text>")


def render(theme, total, first, current, longest, today):
    t = THEMES[theme]
    cur_n, cur_s, cur_e = current
    lon_n, lon_s, lon_e = longest
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 495 195' width='495' height='195'>
  <defs>
    <mask id='ring-mask'>
      <rect width='495' height='195' fill='white'/>
      <ellipse cx='247.5' cy='32' rx='13' ry='18' fill='black'/>
    </mask>
  </defs>
  <rect x='0.5' y='0.5' width='494' height='194' rx='6' fill='{t["bg"]}' stroke='{t["border"]}'/>
  <line x1='165' y1='28' x2='165' y2='170' stroke='{t["divider"]}'/>
  <line x1='330' y1='28' x2='330' y2='170' stroke='{t["divider"]}'/>

  {text(82.5, 80, f"{total:,}", t["text"], 28, 700)}
  {text(82.5, 116, "Total Contributions", t["text"], 14)}
  {text(82.5, 146, f"{fmt(first, today)} - Present", t["muted"], 12)}

  <g mask='url(#ring-mask)'>
    <circle cx='247.5' cy='71' r='40' fill='none' stroke='{t["accent"]}' stroke-width='5'/>
  </g>
  <path transform='translate(235.5 19.5)' d='{FIRE}' fill='{t["fire"]}'/>
  {text(247.5, 81, cur_n, t["text"], 28, 700)}
  {text(247.5, 140, "Current Streak", t["accent"], 14, 700)}
  {text(247.5, 166, fmt_range(cur_s, cur_e, today), t["muted"], 12)}

  {text(412.5, 80, lon_n, t["text"], 28, 700)}
  {text(412.5, 116, "Longest Streak", t["text"], 14)}
  {text(412.5, 146, fmt_range(lon_s, lon_e, today), t["muted"], 12)}
</svg>
"""


def main():
    days = fetch_days()
    result = stats(days)
    os.makedirs(OUT_DIR, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT_DIR, f"{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, *result))
    total, _, current, longest, _ = result
    print(f"total={total} current={current[0]} longest={longest[0]}")


if __name__ == "__main__":
    main()
