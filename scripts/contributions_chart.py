"""Render assets/contributions-per-month.svg from the GitHub contribution calendar.

Private contributions count too (the calendar returns them without repo names).
Needs `gh` logged in, or GH_TOKEN with read:user.
"""
import collections
import datetime as dt
import json
import subprocess
from pathlib import Path

START = dt.date(2026, 2, 1)
QUERY = """query($from:DateTime!,$to:DateTime!){viewer{contributionsCollection(from:$from,to:$to){
contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
OUT = Path(__file__).resolve().parent.parent / "assets" / "contributions-per-month.svg"


def monthly_counts(today: dt.date) -> collections.OrderedDict:
    raw = subprocess.check_output(
        ["gh", "api", "graphql", "-f", f"query={QUERY}",
         "-f", f"from={START}T00:00:00Z", "-f", f"to={today}T23:59:59Z"], text=True)
    weeks = json.loads(raw)["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts = collections.Counter()
    for week in weeks:
        for day in week["contributionDays"]:
            counts[day["date"][:7]] += day["contributionCount"]
    months, cursor = collections.OrderedDict(), START
    while cursor <= today:
        key = cursor.strftime("%Y-%m")
        months[key] = counts.get(key, 0)
        cursor = (cursor.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    return months


def render(months: collections.OrderedDict, today: dt.date) -> str:
    w, h, left, bottom, top = 760, 280, 24, 44, 36
    n, peak = len(months), max(months.values()) or 1
    slot = (w - 2 * left) / n
    bar = slot * 0.58
    plot_h = h - bottom - top
    total = sum(months.values())
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="Contributions per month, {total} in total">',
        "<style>"
        ":root{--bar:#0b6e75;--peak:#e07a1f;--txt:#1b2125;--mut:#5d6a72;--grid:#dde2e6}"
        "@media (prefers-color-scheme:dark){:root{--bar:#5cc6cd;--peak:#f0a35a;--txt:#e6ebee;--mut:#9aa7af;--grid:#2c373d}}"
        "text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}"
        ".t{fill:var(--txt);font-size:15px;font-weight:600}.m{fill:var(--mut);font-size:12px}"
        ".v{fill:var(--txt);font-size:12px;font-weight:600}.g{stroke:var(--grid);stroke-width:1}"
        "</style>",
        f'<text class="t" x="{left}" y="22">Contributions per month · {total:,} since {START.strftime("%b %Y")}</text>',
        f'<line class="g" x1="{left}" x2="{w - left}" y1="{h - bottom}" y2="{h - bottom}"/>',
    ]
    for i, (key, value) in enumerate(months.items()):
        x = left + i * slot + (slot - bar) / 2
        bh = value / peak * plot_h
        y = h - bottom - bh
        fill = "var(--peak)" if value == peak else "var(--bar)"
        label = dt.date.fromisoformat(key + "-01").strftime("%b")
        partial = " *" if key == today.strftime("%Y-%m") else ""
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar:.1f}" height="{bh:.1f}" rx="3" fill="{fill}"/>')
        parts.append(f'<text class="v" x="{x + bar / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle">{value}</text>')
        parts.append(f'<text class="m" x="{x + bar / 2:.1f}" y="{h - bottom + 18}" text-anchor="middle">{label}{partial}</text>')
    parts.append(f'<text class="m" x="{w - left}" y="{h - 8}" text-anchor="end">* month in progress · updated {today}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    today = dt.date.today()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(monthly_counts(today), today))
    print(f"wrote {OUT}")
