"""Render the offline dashboard with embedded styles, logo and aggregate data."""
from pathlib import Path
import base64
import json


def render_dashboard(root, data):
    root = Path(root)
    template = (root/'analysis/dashboard.template.html').read_text()
    css = (root/'analysis/dashboard.css').read_text()
    logo = base64.b64encode((root/'data/reference/rr_logo.svg').read_bytes()).decode()
    markup = template.replace('__DASHBOARD_CSS__', css)
    markup = markup.replace('__RR_LOGO_DATA__', 'data:image/svg+xml;base64,'+logo)
    markup = markup.replace('__AGGREGATE_DATA__',
                            json.dumps(data, separators=(',', ':')).replace('</', '<\\/'))
    path = root/'rr_auction_dashboard.html'
    path.write_text(markup)
    return path
