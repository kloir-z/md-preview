"""
Markdown Preview Server
- ローカルHTTPサーバーでMarkdownファイルをHTMLレンダリング
- http://localhost:3030/view?path=C:/path/to/file.md でアクセス
- ファイル変更時に自動リロード (MD5ポーリング)

Usage:
    python md_server.py [--port 3030]
"""

import argparse
import asyncio
import hashlib
import html
import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote, quote

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
<title>__MD_TITLE__</title>
<link rel="stylesheet" id="hljsTheme" href="/static/hljs/github-dark.min.css">
<link rel="stylesheet" href="/static/app.css?v=__MD_ASSET_VER__">
<script src="/static/highlight.min.js"></script>
<script src="/static/mermaid.min.js"></script>
<script src="/static/app.early.js?v=__MD_ASSET_VER__"></script>
</head>
<body>
<script>
// 描画前のbody依存の早期適用（FOUC回避）。savedMaxWidth等はapp.early.jsが定義済み
// （クラシックスクリプト間でトップレベルconstのレキシカルスコープを共有する）。
if (savedMaxWidth) document.body.style.maxWidth = savedMaxWidth + "px";
if (localStorage.getItem("md-preview-toc-open") === "1") document.body.classList.add("toc-open");
const savedMinimapWidth = localStorage.getItem("md-preview-minimap-width");
if (savedMinimapWidth) document.documentElement.style.setProperty("--minimap-width", savedMinimapWidth + "px");
const savedTocWidth = localStorage.getItem("md-preview-toc-width");
if (savedTocWidth) document.documentElement.style.setProperty("--toc-width", savedTocWidth + "px");
const savedTocSplit = parseFloat(localStorage.getItem("md-preview-toc-split-pct"));
if (savedTocSplit >= 10 && savedTocSplit <= 90) {
  document.documentElement.style.setProperty("--toc-split", savedTocSplit + "%");
}
</script>
<div class="minimap" id="minimap">
  <div class="minimap-content" id="minimapContent"></div>
  <div class="minimap-viewport" id="minimapViewport"></div>
</div>
<div class="minimap-resize" id="minimapResize" title="Drag to resize minimap"></div>
<nav class="toc" id="toc">
  <div class="toc-modes" id="tocModes">
    <button class="toc-mode-btn" id="modeFiles" data-mode="files">Files</button>
    <button class="toc-mode-btn" id="modeOutline" data-mode="outline">Outline</button>
    <button class="toc-mode-btn" id="modeBoth" data-mode="both" title="Files + Outline">Both</button>
  </div>
  <div class="toc-panes" id="tocPanes">
    <div class="toc-pane" id="paneFiles" style="display:none"></div>
    <div class="toc-split-resize" id="tocSplitResize" title="Drag to resize"></div>
    <div class="toc-pane" id="paneOutline"></div>
  </div>
</nav>
<button class="toc-toggle" id="tocToggle" title="Toggle sidebar (Ctrl+\\)">&#9776;</button>
<div class="toc-resize" id="tocResize" title="Drag to resize sidebar"></div>
<button class="edit-btn" id="editBtn" title="Edit (Ctrl+E)">&#9998;</button>
<button class="settings-btn" id="settingsBtn" title="Settings">&#9881;</button>
<div class="edit-panel" id="editPanel">
  <textarea class="edit-textarea" id="editTextarea" spellcheck="false"></textarea>
</div>
<div class="edit-controls" id="editControls">
  <span class="edit-status" id="editStatus"></span>
  <button class="cancel" id="editCancelBtn">Cancel (Esc)</button>
  <button class="save" id="editSaveBtn">Save (Ctrl+S)</button>
</div>
<div class="settings-overlay" id="settingsOverlay"></div>
<div class="settings-modal" id="settingsModal">
  <div class="settings-modal-header">
    <h3>Settings</h3>
    <button class="settings-close" id="settingsClose">&times;</button>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Theme</div>
    <select class="theme-select" id="themeSelect"></select>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Code Theme</div>
    <select class="theme-select" id="codeThemeSelect"></select>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Text Color</div>
    <div class="settings-color-row"><label>Body</label><select class="heading-color-select" id="fgColor"></select></div>
    <div class="settings-slider-row"><label>Brightness</label><input type="range" id="fgBrightness" min="40" max="100" value="100" step="5"><span class="slider-value" id="fgBrightnessValue">100%</span></div>
    <div class="settings-color-row"><label>Code</label><select class="heading-color-select" id="codeColor"></select></div>
    <div class="settings-section-title" style="display:flex;justify-content:space-between;align-items:center;margin-top:14px;">Heading Colors <button class="settings-btn-apply" id="shuffleHeadingBtn" style="margin:0;padding:2px 10px;font-size:11px;">Shuffle</button></div>
    <div class="settings-color-row"><label>H1</label><select class="heading-color-select" id="h1Color"></select></div>
    <div class="settings-color-row"><label>H2</label><select class="heading-color-select" id="h2Color"></select></div>
    <div class="settings-color-row"><label>H3</label><select class="heading-color-select" id="h3Color"></select></div>
    <div class="settings-color-row"><label>H4</label><select class="heading-color-select" id="h4Color"></select></div>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Layout</div>
    <div class="settings-slider-row">
      <label>List margin</label>
      <input type="range" id="listMarginSlider" min="0" max="32" value="16" step="1">
      <span class="slider-value" id="listMarginValue">16px</span>
    </div>
    <div class="settings-slider-row">
      <label>Max width</label>
      <input type="range" id="maxWidthSlider" min="600" max="1800" value="800" step="50">
      <span class="slider-value" id="maxWidthValue">800px</span>
    </div>
    <div class="settings-slider-row">
      <label>Minimap width</label>
      <input type="range" id="minimapWidthSlider" min="60" max="200" value="80" step="5">
      <span class="slider-value" id="minimapWidthValue">80px</span>
    </div>
  </div>
</div>
<div class="file-path" id="filePathEl">__MD_FILEPATH__</div>
<main id="mdContent">
__MD_CONTENT__
</main>
<script id="md-data" type="application/json">__MD_DATA__</script>
<script src="/static/app.js?v=__MD_ASSET_VER__"></script>
</body>
</html>
"""

md_extensions = ["fenced_code", "tables", "toc", "nl2br", "sane_lists"]

# キャッシュバスティング用: app.css/js を外出ししたため、/static は max-age=86400 で
# 強くキャッシュされる。これらの URL に ?v=<mtime> を付け、ファイル更新時に必ず再取得させる。
_ASSET_FILES = ("app.css", "app.early.js", "app.js")


def _asset_version() -> str:
    """外出しした静的アセットの最新mtime(ns)を返す。更新検知のキャッシュバスター。"""
    latest = 0
    for name in _ASSET_FILES:
        try:
            m = (STATIC_DIR / name).stat().st_mtime_ns
            if m > latest:
                latest = m
        except OSError:
            pass
    return str(latest)


def render_markdown(filepath: str) -> tuple[str, str]:
    """Markdownファイルを読み込んでHTML + ハッシュを返す"""
    path = Path(filepath)
    if not path.exists():
        return f"<h1>File not found</h1><p>{filepath}</p>", ""
    text = path.read_text(encoding="utf-8")
    html = markdown.markdown(text, extensions=md_extensions)
    content_hash = hashlib.md5(text.encode()).hexdigest()
    return html, content_hash


# ファイルシステム走査時に降りないディレクトリ（重い/無関係なもの）
_SCAN_EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".idea",
    ".vscode", "dist", "build", ".next", ".cache", ".tox", ".mypy_cache",
    ".pytest_cache", "site-packages",
}
# フォールバック走査の上限件数（巨大ツリーで固まらないための安全弁）
_SCAN_MAX_FILES = 1000


def _scan_dir_markdown(base: Path) -> dict:
    """gitを使わず、baseフォルダ以下の.mdをファイルシステム走査で列挙する。

    rel/absはgit版と同じく前方スラッシュ表記で返す（フロントのbuildTree・
    選択ハイライトがwindow.__md.path（前方スラッシュ）と整合するように）。
    """
    root = base.resolve()
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 除外ディレクトリと隠しディレクトリは降りない（in-placeでprune）
        dirnames[:] = [
            d for d in dirnames
            if d not in _SCAN_EXCLUDE_DIRS and not d.startswith(".")
        ]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                p = Path(dirpath) / fn
                files.append({
                    "rel": p.relative_to(root).as_posix(),
                    "abs": p.resolve().as_posix(),
                })
                if len(files) >= _SCAN_MAX_FILES:
                    files.sort(key=lambda x: x["rel"].lower())
                    return {"root": root.as_posix(), "files": files}
    files.sort(key=lambda x: x["rel"].lower())
    return {"root": root.as_posix(), "files": files}


def scan_root_for(filepath: str) -> Path:
    """走査ルート（=タブタイトルに使う最上位ディレクトリ）を返す。
    gitリポジトリ内ならトップ階層（`git rev-parse --show-toplevel`）、
    git管理外/gitが無ければ開いたファイルのフォルダ。"""
    base = Path(filepath).parent
    scan_root = base
    try:
        top = subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if top.returncode == 0 and top.stdout.strip():
            scan_root = Path(top.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return scan_root


def _title_for(filepath: str) -> str:
    """タブタイトル: 走査ルート（最上位ディレクトリ）名。取れなければファイル名。"""
    root = scan_root_for(filepath)
    return root.name or str(root) or Path(filepath).name


def list_repo_markdown(filepath: str) -> dict:
    """filepathの周辺にある.mdファイル一覧を返す（Filesサイドバー用）。

    走査ルートの決め方:
      - gitリポジトリ内 → リポジトリのトップ階層（`git rev-parse --show-toplevel`）
      - git管理外/gitが無い → 開いたファイルのフォルダ
    決めたルート以下をファイルシステム走査して.mdを列挙する。追跡/未追跡や
    .gitignoreの有無に関係なく全`.md`が対象（gitはルート決定にのみ使用）。
    ただし.git/node_modules等は除外、件数上限あり（_scan_dir_markdown）。
    baseが存在しない場合のみ {"root": None, "files": []}。
    """
    empty = {"root": None, "files": []}
    base = Path(filepath).parent
    if not base.exists():
        return empty
    try:
        return _scan_dir_markdown(scan_root_for(filepath))
    except OSError:
        return empty


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
            title = _title_for(filepath)
            # per-request データは #md-data(JSON) として注入。CSS/JS を外出ししたので
            # .format() の波括弧二重化は不要になり、マーカーの .replace() で展開する。
            # content は最後に置換し、本文中に偶然マーカーがあっても波及させない。
            md_data = json.dumps({
                "path": filepath.replace("\\", "/"),
                "hash": content_hash,
            })
            page = (HTML_TEMPLATE
                    .replace("__MD_ASSET_VER__", _asset_version())
                    .replace("__MD_TITLE__", html.escape(title))
                    .replace("__MD_FILEPATH__", html.escape(filepath))
                    .replace("__MD_DATA__", md_data)
                    .replace("__MD_CONTENT__", html_content))
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

        if parsed.path == "/content":
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            path = Path(filepath)
            if not path.exists():
                self.send_error(404, "File not found")
                return
            text = path.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.write(text.encode("utf-8"))
            return

        if parsed.path == "/files":
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            result = list_repo_markdown(filepath)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.write(json.dumps(result).encode())
            return

        if parsed.path == "/render":
            # レンダリング済みHTML断片 + ハッシュをJSONで返す（シームレスなファイル切替用）。
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            html_content, content_hash = render_markdown(filepath)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.write(json.dumps({
                "html": html_content,
                "hash": content_hash,
                "title": _title_for(filepath),
            }).encode())
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

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/save":
            params = parse_qs(parsed.query)
            filepath = params.get("path", [None])[0]
            if not filepath:
                self.send_error(400, "Missing path parameter")
                return
            filepath = unquote(filepath)
            path = Path(filepath)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                path.write_text(body, encoding="utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                new_hash = hashlib.md5(body.encode()).hexdigest()
                self.write(json.dumps({"ok": True, "hash": new_hash}).encode())
            except Exception as e:
                self.send_error(500, f"Save failed: {e}")
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

    # ThreadingHTTPServer: 大きな静的ファイル(mermaid.min.js 3.3MB)配信中も
    # ブラウザのポーリング/他リクエストでブロックしないよう各接続を別スレッドで処理する。
    server = ThreadingHTTPServer(("127.0.0.1", args.port), MarkdownHandler)
    print(f"Markdown server running at http://localhost:{args.port}")

    if args.file:
        filepath = str(Path(args.file).resolve())
        # パスにスペースやバックスラッシュ・日本語が含まれるとブラウザがURLを誤解釈して
        # 開けないため、必ずURLエンコードする（git管理外のDocuments配下等で頻発）。
        url = f"http://localhost:{args.port}/view?path={quote(filepath, safe='')}"
        print(f"Opening: {url}")
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
