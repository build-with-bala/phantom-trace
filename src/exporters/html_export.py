"""Interactive HTML dashboard report."""

from datetime import datetime
from pathlib import Path
from src.models import PersonProfile

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phantom Trace - {query}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0f;color:#c8c8d0;font-family:'JetBrains Mono',monospace}}
.container{{max-width:1200px;margin:0 auto;padding:2rem}}
.header{{text-align:center;padding:3rem 0;border-bottom:1px solid #1a1a2e}}
.header h1{{font-size:2.5rem;background:linear-gradient(135deg,#00ff88,#00aaff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin:2rem 0}}
.stat-card{{background:#12121a;border:1px solid #1a1a2e;border-radius:12px;padding:1.5rem;text-align:center}}
.stat-card .number{{font-size:2rem;color:#00ff88;font-weight:bold}}
.stat-card .label{{color:#666;font-size:.85rem;margin-top:.5rem}}
.site-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem;margin:2rem 0}}
.site-card{{background:#12121a;border:1px solid #1a1a2e;border-radius:8px;padding:1rem;transition:border-color .2s}}
.site-card:hover{{border-color:#00ff88}}
.site-card .name{{color:#00ff88;font-weight:bold}}
.site-card .url a{{color:#00aaff;text-decoration:none;font-size:.8rem}}
.category{{display:inline-block;background:#1a1a2e;color:#888;padding:2px 8px;border-radius:4px;font-size:.75rem;margin-top:.5rem}}
.bar{{width:100%;height:24px;background:#1a1a2e;border-radius:12px;overflow:hidden;margin:1rem 0}}
.fill{{height:100%;background:linear-gradient(90deg,#ff4444,#ffaa00,#00ff88);border-radius:12px}}
.footer{{text-align:center;padding:2rem;color:#333;font-size:.8rem;border-top:1px solid #1a1a2e;margin-top:3rem}}
</style>
</head>
<body>
<div class="container">
<div class="header"><h1>PHANTOM TRACE</h1><p style="color:#666;margin-top:.5rem">OSINT Intelligence Report</p>
<p style="color:#444;margin-top:1rem">Target: <strong style="color:#00ff88">{query}</strong></p></div>
<div class="stats">
<div class="stat-card"><div class="number">{found}</div><div class="label">Found</div></div>
<div class="stat-card"><div class="number">{checked}</div><div class="label">Checked</div></div>
<div class="stat-card"><div class="number">{confidence}%</div><div class="label">Confidence</div></div>
</div>
<h2 style="color:#00aaff;margin:1rem 0">Confidence</h2>
<div class="bar"><div class="fill" style="width:{confidence}%"></div></div>
<h2 style="color:#00aaff;margin:1rem 0">Profiles</h2>
<div class="site-grid">{cards}</div>
<div class="footer">Phantom Trace v1.0.0</div>
</div></body></html>"""


def export_html(profile: PersonProfile, output_path: str):
    cards = ""
    for s in sorted(profile.sites_found, key=lambda x: x.site):
        cards += f'<div class="site-card"><div class="name">{s.site.title()}</div><div class="url"><a href="{s.url}" target="_blank">{s.url}</a></div><span class="category">{s.category}</span></div>'

    html = TEMPLATE.format(
        query=profile.query,
        found=profile.total_found,
        checked=profile.total_checked,
        confidence=int(profile.confidence_score * 100),
        cards=cards,
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
