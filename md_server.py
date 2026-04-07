"""
Markdown Preview Server
- ローカルHTTPサーバーでMarkdownファイルをHTMLレンダリング
- http://localhost:3030/view?path=C:/path/to/file.md でアクセス
- ファイル変更時に自動リロード (WebSocket)

Usage:
    python scripts/md_server.py [--port 3030]
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

import mimetypes
import markdown

from config import DEFAULT_PORT
STATIC_DIR = Path(__file__).parent / "static"

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="/static/monokai.min.css">
<script src="/static/highlight.min.js"></script>
<style>
  :root {{
    --bg: #272822;
    --fg: #d8d8d2;
    --border: #3e3f3a;
    --code-bg: #1e1f1c;
    --blockquote-fg: #8f908a;
    --blockquote-border: #3e3f3a;
    --link: #66c2b5;
    --file-path: #8f908a;
    --table-stripe: #2e2f2a;
    --heading: #d4a76a;
    --accent: #ae9fcc;
  }}
  body {{
    max-width: 800px;
    margin: 40px auto;
    padding: 0 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: var(--fg);
    background: var(--bg);
  }}
  a {{ color: var(--link); }}
  h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; }}
  h1 {{ color: var(--heading); border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
  h2 {{ color: var(--heading); border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
  h3, h4, h5, h6 {{ color: var(--heading); }}
  code {{
    background: var(--code-bg);
    color: var(--accent);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 85%;
  }}
  pre {{
    background: var(--code-bg);
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
  }}
  pre code {{ background: none; padding: 0; font-size: 14px; }}
  blockquote {{
    border-left: 4px solid var(--blockquote-border);
    margin: 0;
    padding: 0.5em 1em;
    color: var(--blockquote-fg);
  }}
  table {{ border-collapse: collapse; width: 100%; }}
  table th, table td {{
    border: 1px solid var(--border);
    padding: 6px 13px;
  }}
  table th {{ font-weight: 600; }}
  table tr:nth-child(even) {{ background: var(--table-stripe); }}
  img {{ max-width: 100%; }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 2em 0; }}
  .file-path {{
    font-size: 12px;
    color: var(--file-path);
    margin-bottom: 1em;
    word-break: break-all;
  }}
  /* checkbox style for task lists */
  li input[type="checkbox"] {{ margin-right: 0.5em; }}
  /* settings panel */
  .settings-btn {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--code-bg);
    color: var(--fg);
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0.6;
    transition: opacity 0.2s;
  }}
  .settings-btn:hover {{ opacity: 1; }}
  .settings-panel {{
    position: fixed;
    bottom: 64px;
    right: 20px;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 0;
    z-index: 1000;
    min-width: 180px;
    display: none;
  }}
  .settings-panel.open {{ display: block; }}
  .settings-panel-title {{
    padding: 4px 16px 8px;
    font-size: 11px;
    color: var(--file-path);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .theme-item {{
    padding: 6px 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--fg);
  }}
  .theme-item:hover {{ background: var(--bg); }}
  .theme-item.active {{ color: var(--link); }}
  .theme-item .check {{ width: 16px; text-align: center; }}
</style>
<script>
const THEMES = {{
  monokai: {{
    name: "Monokai",
    "--bg": "#272822", "--fg": "#d8d8d2", "--border": "#3e3f3a",
    "--code-bg": "#1e1f1c", "--blockquote-fg": "#8f908a",
    "--blockquote-border": "#3e3f3a", "--link": "#66c2b5",
    "--file-path": "#8f908a", "--table-stripe": "#2e2f2a",
    "--heading": "#d4a76a", "--accent": "#ae9fcc",
  }},
  github_dark: {{
    name: "GitHub Dark",
    "--bg": "#0d1117", "--fg": "#e6edf3", "--border": "#30363d",
    "--code-bg": "#161b22", "--blockquote-fg": "#8b949e",
    "--blockquote-border": "#30363d", "--link": "#58a6ff",
    "--file-path": "#8b949e", "--table-stripe": "#161b22",
    "--heading": "#e6edf3", "--accent": "#bc8cff",
  }},
  dracula: {{
    name: "Dracula",
    "--bg": "#282a36", "--fg": "#f8f8f2", "--border": "#44475a",
    "--code-bg": "#21222c", "--blockquote-fg": "#6272a4",
    "--blockquote-border": "#44475a", "--link": "#8be9fd",
    "--file-path": "#6272a4", "--table-stripe": "#2d2f3d",
    "--heading": "#bd93f9", "--accent": "#ff79c6",
  }},
  nord: {{
    name: "Nord",
    "--bg": "#2e3440", "--fg": "#d8dee9", "--border": "#3b4252",
    "--code-bg": "#272c36", "--blockquote-fg": "#7b88a1",
    "--blockquote-border": "#3b4252", "--link": "#88c0d0",
    "--file-path": "#7b88a1", "--table-stripe": "#333a47",
    "--heading": "#81a1c1", "--accent": "#b48ead",
  }},
  solarized_dark: {{
    name: "Solarized Dark",
    "--bg": "#002b36", "--fg": "#839496", "--border": "#073642",
    "--code-bg": "#01313f", "--blockquote-fg": "#657b83",
    "--blockquote-border": "#073642", "--link": "#268bd2",
    "--file-path": "#657b83", "--table-stripe": "#073642",
    "--heading": "#b58900", "--accent": "#2aa198",
  }},
  gruvbox_dark: {{
    name: "Gruvbox Dark",
    "--bg": "#282828", "--fg": "#ebdbb2", "--border": "#3c3836",
    "--code-bg": "#1d2021", "--blockquote-fg": "#a89984",
    "--blockquote-border": "#3c3836", "--link": "#83a598",
    "--file-path": "#a89984", "--table-stripe": "#302e2b",
    "--heading": "#fabd2f", "--accent": "#d3869b",
  }},
  catppuccin_mocha: {{
    name: "Catppuccin Mocha",
    "--bg": "#1e1e2e", "--fg": "#cdd6f4", "--border": "#313244",
    "--code-bg": "#181825", "--blockquote-fg": "#a6adc8",
    "--blockquote-border": "#313244", "--link": "#89b4fa",
    "--file-path": "#a6adc8", "--table-stripe": "#232336",
    "--heading": "#cba6f7", "--accent": "#f5c2e7",
  }},
  tokyo_night: {{
    name: "Tokyo Night",
    "--bg": "#1a1b26", "--fg": "#a9b1d6", "--border": "#292e42",
    "--code-bg": "#16161e", "--blockquote-fg": "#565f89",
    "--blockquote-border": "#292e42", "--link": "#7aa2f7",
    "--file-path": "#565f89", "--table-stripe": "#1f2030",
    "--heading": "#bb9af7", "--accent": "#f7768e",
  }},
}};

function applyTheme(key) {{
  const theme = THEMES[key];
  if (!theme) return;
  const root = document.documentElement;
  Object.keys(theme).forEach(k => {{
    if (k.startsWith("--")) root.style.setProperty(k, theme[k]);
  }});
}}

const savedTheme = localStorage.getItem("md-preview-theme") || "monokai";
applyTheme(savedTheme);
</script>
</head>
<body>
<button class="settings-btn" id="settingsBtn" title="Settings">&#9881;</button>
<div class="settings-panel" id="settingsPanel">
  <div class="settings-panel-title">Theme</div>
</div>
<div class="file-path">{filepath}</div>
{content}
<script>
hljs.highlightAll();

// --- Theme settings panel ---
(function() {{
  const panel = document.getElementById("settingsPanel");
  const btn = document.getElementById("settingsBtn");
  let currentTheme = localStorage.getItem("md-preview-theme") || "monokai";

  function renderThemeList() {{
    const items = panel.querySelectorAll(".theme-item");
    items.forEach(el => el.remove());
    Object.entries(THEMES).forEach(([key, theme]) => {{
      const div = document.createElement("div");
      div.className = "theme-item" + (key === currentTheme ? " active" : "");
      div.innerHTML = '<span class="check">' + (key === currentTheme ? "&#10003;" : "") + "</span>" + theme.name;
      div.addEventListener("click", () => {{
        currentTheme = key;
        applyTheme(key);
        localStorage.setItem("md-preview-theme", key);
        renderThemeList();
      }});
      panel.appendChild(div);
    }});
  }}

  btn.addEventListener("click", (e) => {{
    e.stopPropagation();
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) renderThemeList();
  }});

  document.addEventListener("click", (e) => {{
    if (!panel.contains(e.target) && e.target !== btn) {{
      panel.classList.remove("open");
    }}
  }});

  renderThemeList();
}})();

(function() {{
  let hash = "{content_hash}";
  const path = "{filepath_js}";
  setInterval(async () => {{
    try {{
      const res = await fetch("/hash?path=" + encodeURIComponent(path));
      const data = await res.json();
      if (data.hash && data.hash !== hash) {{
        hash = data.hash;
        location.reload();
      }}
    }} catch(e) {{}}
  }}, 1000);
}})();
</script>
</body>
</html>
"""

md_extensions = ["fenced_code", "tables", "toc", "nl2br", "sane_lists"]


def render_markdown(filepath: str) -> tuple[str, str]:
    """Markdownファイルを読み込んでHTML + ハッシュを返す"""
    path = Path(filepath)
    if not path.exists():
        return f"<h1>File not found</h1><p>{filepath}</p>", ""
    text = path.read_text(encoding="utf-8")
    html = markdown.markdown(text, extensions=md_extensions)
    content_hash = hashlib.md5(text.encode()).hexdigest()
    return html, content_hash


class MarkdownHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/view":
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            html_content, content_hash = render_markdown(filepath)
            title = Path(filepath).name
            page = HTML_TEMPLATE.format(
                title=title,
                filepath=filepath,
                content=html_content,
                content_hash=content_hash,
                filepath_js=filepath.replace("\\", "/"),
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.write(page.encode())
            return

        if parsed.path == "/hash":
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            _, content_hash = render_markdown(filepath)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.write(json.dumps({"hash": content_hash}).encode())
            return

        if parsed.path.startswith("/static/"):
            filename = parsed.path[len("/static/"):]
            filepath = STATIC_DIR / filename
            if filepath.exists() and filepath.is_file():
                content_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.write(filepath.read_bytes())
            else:
                self.send_error(404)
            return

        if parsed.path == "/open":
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            self.send_response(302)
            self.send_header("Location", f"/view?path={filepath}")
            self.end_headers()
            return

        self.send_error(404)

    def write(self, data: bytes):
        try:
            self.wfile.write(data)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        # quiet logging
        pass


def main():
    parser = argparse.ArgumentParser(description="Markdown Preview Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("file", nargs="?", help="Open a specific .md file")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), MarkdownHandler)
    print(f"Markdown server running at http://localhost:{args.port}")

    if args.file:
        filepath = str(Path(args.file).resolve())
        url = f"http://localhost:{args.port}/view?path={filepath}"
        print(f"Opening: {url}")
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
