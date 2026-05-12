import os
from pathlib import Path
import dash
from dash import html

_PROJECT_ROOT = Path(__file__).parent.parent
_PAGES_FOLDER = str(_PROJECT_ROOT / "ui" / "pages")

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder=_PAGES_FOLDER,
    suppress_callback_exceptions=True,
)

app.layout = html.Div(
    [dash.page_container],
    style={'fontFamily': 'sans-serif', 'maxWidth': '1400px',
           'margin': '0 auto', 'padding': '0 16px'},
)


def run() -> None:
    port = int(os.getenv("PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == '__main__':
    run()
