"""
Markdown Preview Server
- ローカルHTTPサーバーでMarkdownファイルをHTMLレンダリング
- http://localhost:3030/view?path=C:/path/to/file.md でアクセス
- ファイル変更時に自動リロード (MD5ポーリング)

Usage:
    python md_server.py [--port 3030]
"""

import argparse
import hashlib
import html
import json
import os
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote, quote

import mimetypes
import markdown

from config import DEFAULT_PORT
# /static のパストラバーサル判定（is_relative_to）のため解決済み絶対パスで持つ
STATIC_DIR = (Path(__file__).parent / "static").resolve()

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


def _read_text_lenient(path: Path) -> tuple[str, bytes]:
    """ファイルをbytesで読み、UTF-8(BOM可)→CP932の順で試してデコードする。
    どちらでも読めなければerrors="replace"で落とさず表示する
    （非UTF-8ファイルでUnicodeDecodeErrorになり応答不能だったのを解消）。
    返り値は (テキスト, 生bytes)。ハッシュは生bytesから計算する。"""
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp932"):
        try:
            return data.decode(enc), data
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace"), data


def file_hash(filepath: str) -> str:
    """ファイル生bytesのMD5（変更検知ポーリング用）。無い/読めない場合は空文字。

    以前はtext.encode()のMD5だったが、/hashが毎秒Markdownをフルレンダリング
    していた無駄をなくすため、レンダリング不要な生bytesのMD5に統一した。
    """
    try:
        return hashlib.md5(Path(filepath).read_bytes()).hexdigest()
    except OSError:
        return ""


def render_markdown(filepath: str) -> tuple[str, str]:
    """Markdownファイルを読み込んでHTML + ハッシュ（生bytesのMD5）を返す"""
    path = Path(filepath)
    if not path.exists():
        return f"<h1>File not found</h1><p>{html.escape(filepath)}</p>", ""
    try:
        text, data = _read_text_lenient(path)
    except OSError as e:
        return f"<h1>Read error</h1><p>{html.escape(str(e))}</p>", ""
    # markdownライブラリに渡す前に行末をLFへ正規化（CRLFファイル対策）
    html_out = markdown.markdown(text.replace("\r\n", "\n"), extensions=md_extensions)
    return html_out, hashlib.md5(data).hexdigest()


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
        # 除外ディレクトリは降りない（in-placeでprune）。隠しディレクトリ（.claude等）は
        # 一律除外せず、ノイズ系のみ_SCAN_EXCLUDE_DIRSで明示除外する。
        dirnames[:] = [d for d in dirnames if d not in _SCAN_EXCLUDE_DIRS]
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


# scan_root_for の結果キャッシュ（base ディレクトリ → 走査ルート）。
# 走査ルートはセッション中まず変わらないため、base単位でキャッシュして
# 1ページ表示で /view・/files・/render から繰り返される探索を初回1回に抑える。
_scan_root_cache: dict[str, Path] = {}


def _find_repo_top(base: Path) -> Path | None:
    """baseから親方向に`.git`（ディレクトリ or worktree用ファイル）を探し、
    見つかればそれを含むディレクトリ（=リポジトリのトップ階層）を返す。
    `git rev-parse --show-toplevel`の純Python版。git.exe不要・起動コストゼロ。
    見つからなければNone。"""
    for d in (base, *base.parents):
        if (d / ".git").exists():
            return d
    return None


def scan_root_for(filepath: str) -> Path:
    """走査ルート（=タブタイトルに使う最上位ディレクトリ）を返す。
    gitリポジトリ内ならトップ階層（親方向に`.git`を探索）、
    git管理外なら開いたファイルのフォルダ。

    git.exeは使わず純Pythonで判定する（サブプロセス起動のコスト・コンソール
    ちらつき・タイムアウトを回避）。結果はbaseディレクトリ単位でキャッシュする。"""
    base = Path(filepath).parent
    key = str(base)
    cached = _scan_root_cache.get(key)
    if cached is not None:
        return cached
    scan_root = _find_repo_top(base) or base
    _scan_root_cache[key] = scan_root
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
    # HTTP/1.1でKeep-Aliveを有効化。HTTP/1.0は接続使い捨てで、ページ表示のたびに
    # 全リクエスト（HTML/CSS/JS/ポーリング）がTCP接続を張り直していた。
    # 1.1では全応答にContent-Lengthが必須（無いとブラウザが応答完了を判定できない）。
    protocol_version = "HTTP/1.1"
    # ブラウザが掴んだままのアイドル接続からスレッドを解放する
    timeout = 75

    # ローカル専用サーバーだがブラウザ経由で外部サイトから攻撃可能なため検証する。
    #  - Hostチェック: DNSリバインディング対策（攻撃者ドメインを127.0.0.1に解決させ
    #    同一オリジン扱いで/content等から任意ファイルを読み取る手口を防ぐ）
    #  - Originチェック(POST): CSRF対策（外部サイトからの/save POSTによる
    #    任意ファイル書き込みを防ぐ）
    _ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "")
        try:
            hostname = urlparse(f"//{host}").hostname or ""
        except ValueError:
            return False
        return hostname in self._ALLOWED_HOSTNAMES

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:  # 同一オリジンのfetchや非ブラウザクライアントはOriginを送らないことがある
            return True
        try:
            hostname = urlparse(origin).hostname or ""
        except ValueError:
            return False
        return hostname in self._ALLOWED_HOSTNAMES

    def _send(self, code: int, ctype: str, body: bytes, cache: str = "no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.write(body)

    def _query_path(self, parsed) -> str | None:
        """クエリのpathパラメータを返す。無ければ400を送ってNone。
        parse_qsがデコード済みのため、以前あった二重unquoteは行わない
        （%を含むファイル名が壊れるため）。"""
        filepath = parse_qs(parsed.query).get("path", [None])[0]
        if not filepath:
            self.send_error(400, "Missing path parameter")
            return None
        return filepath

    def do_GET(self):
        if not self._host_ok():
            self.send_error(403, "Forbidden")
            return
        parsed = urlparse(self.path)

        if parsed.path == "/view":
            filepath = self._query_path(parsed)
            if filepath is None:
                return
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
            self._send(200, "text/html; charset=utf-8", page.encode())
            return

        if parsed.path == "/hash":
            filepath = self._query_path(parsed)
            if filepath is None:
                return
            self._send(200, "application/json", json.dumps({"hash": file_hash(filepath)}).encode())
            return

        if parsed.path == "/content":
            filepath = self._query_path(parsed)
            if filepath is None:
                return
            path = Path(filepath)
            if not path.exists():
                self.send_error(404, "File not found")
                return
            try:
                text, _ = _read_text_lenient(path)
            except OSError as e:
                self.send_error(500, f"Read failed: {e}")
                return
            self._send(200, "text/plain; charset=utf-8", text.encode("utf-8"))
            return

        if parsed.path == "/files":
            filepath = self._query_path(parsed)
            if filepath is None:
                return
            result = list_repo_markdown(filepath)
            self._send(200, "application/json", json.dumps(result).encode())
            return

        if parsed.path == "/render":
            # レンダリング済みHTML断片 + ハッシュをJSONで返す（シームレスなファイル切替用）。
            filepath = self._query_path(parsed)
            if filepath is None:
                return
            html_content, content_hash = render_markdown(filepath)
            self._send(200, "application/json", json.dumps({
                "html": html_content,
                "hash": content_hash,
                "title": _title_for(filepath),
            }).encode())
            return

        if parsed.path.startswith("/static/"):
            filename = unquote(parsed.path[len("/static/"):])
            target = (STATIC_DIR / filename).resolve()
            # パストラバーサル対策: 解決後のパスがstatic/配下でなければ拒否
            # （以前は /static/../../../Windows/win.ini 等が素通りしていた）
            if not (target.is_relative_to(STATIC_DIR) and target.is_file()):
                self.send_error(404)
                return
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self._send(200, content_type, target.read_bytes(), cache="public, max-age=86400")
            return

        if parsed.path == "/open":
            filepath = self._query_path(parsed)
            if filepath is None:
                return
            self.send_response(302)
            # デコード済みの値を再エンコードして埋める（以前は生のまま埋めていて
            # スペースや日本語を含むパスでLocationが壊れていた）
            self.send_header("Location", f"/view?path={quote(filepath, safe='')}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_error(404)

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            self.send_error(403, "Forbidden")
            return
        parsed = urlparse(self.path)

        if parsed.path == "/save":
            filepath = self._query_path(parsed)
            if filepath is None:
                return
            path = Path(filepath)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                # 行末を既存ファイルに合わせる: textareaは常にLFを返すため、そのまま
                # 書くとCRLFファイルの行末が保存のたびに全行書き換わってしまう。
                # （以前はwrite_textの改行変換でWindowsでは常にCRLF化＝逆にLFファイルが壊れていた）
                text = body.replace("\r\n", "\n")
                try:
                    existing = path.read_bytes() if path.exists() else b""
                except OSError:
                    existing = b""
                if b"\r\n" in existing:
                    text = text.replace("\n", "\r\n")
                out = text.encode("utf-8")
                # アトミック保存: 一時ファイルに書いてからos.replaceで差し替え
                # （書き込み途中の失敗で元ファイルが破損するのを防ぐ）
                tmp = path.with_name(path.name + ".md-save-tmp")
                try:
                    tmp.write_bytes(out)
                    os.replace(tmp, path)
                except BaseException:
                    tmp.unlink(missing_ok=True)
                    raise
                new_hash = hashlib.md5(out).hexdigest()
                self._send(200, "application/json", json.dumps({"ok": True, "hash": new_hash}).encode())
            except Exception as e:
                self.send_error(500, f"Save failed: {e}")
            return

        self.send_error(404)

    def write(self, data: bytes):
        try:
            self.wfile.write(data)
        except ConnectionError:
            # クライアント切断（タブを閉じた・リロード中断等）は正常系として無視
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
    print(f"Markdown server running at http://127.0.0.1:{args.port}")

    if args.file:
        filepath = str(Path(args.file).resolve())
        # パスにスペースやバックスラッシュ・日本語が含まれるとブラウザがURLを誤解釈して
        # 開けないため、必ずURLエンコードする（git管理外のDocuments配下等で頻発）。
        # localhostだとブラウザがIPv6(::1)を先に試して約200msフォールバック待ちが発生する
        # （サーバーは127.0.0.1のIPv4のみバインド）ため、127.0.0.1を直指定する。
        url = f"http://127.0.0.1:{args.port}/view?path={quote(filepath, safe='')}"
        print(f"Opening: {url}")
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
