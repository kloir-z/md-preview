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
<title>{title}</title>
<link rel="stylesheet" id="hljsTheme" href="/static/hljs/github-dark.min.css">
<script src="/static/highlight.min.js"></script>
<script src="/static/mermaid.min.js"></script>
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
    --h1-color: var(--heading);
    --h2-color: var(--heading);
    --h3-color: var(--heading);
    --h4-color: var(--heading);
    --accent: #ae9fcc;
    --list-margin: 16px;
    --minimap-width: 80px;
    --toc-width: 240px;
  }}
  body {{
    max-width: 800px;
    margin: 40px auto;
    padding: 0 calc(var(--minimap-width) + 20px) 0 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: var(--fg);
    background: var(--bg);
  }}
  a {{ color: var(--link); }}
  h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; }}
  h1 {{ color: var(--h1-color); border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
  h2 {{ color: var(--h2-color); border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
  h3 {{ color: var(--h3-color); }}
  h4, h5, h6 {{ color: var(--h4-color); }}
  code {{
    background: var(--code-bg);
    color: var(--accent);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 97%;
  }}
  pre {{
    background: var(--code-bg);
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
  }}
  pre code {{ background: none; padding: 0; font-size: 14px; }}
  /* hljsテーマCSSの .hljs 背景/余白を打ち消し、コードブロック背景はアプリテーマの
     --code-bg に統一する（テーマ切替で背景がばらつかないようにするため高詳細度で指定）。
     hljsテーマはトークン色のみを担当する。 */
  #mdContent pre code.hljs {{ background: transparent; padding: 0; }}
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
  li {{ margin-bottom: var(--list-margin); }}
  /* settings panel */
  .settings-btn {{
    position: fixed;
    bottom: 20px;
    right: 100px;
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
  /* settings modal */
  .settings-overlay {{
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: none;
  }}
  .settings-overlay.open {{ display: block; }}
  .settings-modal {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    z-index: 2001;
    width: 440px;
    max-height: 80vh;
    overflow-y: auto;
    display: none;
    color: var(--fg);
  }}
  .settings-modal.open {{ display: block; }}
  .settings-modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }}
  .settings-modal-header h3 {{
    margin: 0;
    color: var(--heading);
  }}
  .settings-close {{
    background: none;
    border: none;
    color: var(--fg);
    font-size: 20px;
    cursor: pointer;
    padding: 0 4px;
    opacity: 0.6;
  }}
  .settings-close:hover {{ opacity: 1; }}
  .settings-section {{
    margin-bottom: 20px;
  }}
  .settings-section-title {{
    font-size: 11px;
    color: var(--file-path);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }}
  .theme-select {{
    width: 100%;
    padding: 6px 8px;
    font-size: 14px;
    color: var(--fg);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    outline: none;
  }}
  .theme-select:focus {{ border-color: var(--link); }}
  .settings-textarea {{
    width: 100%;
    height: 100px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 8px;
    font-family: monospace;
    font-size: 12px;
    resize: vertical;
    box-sizing: border-box;
  }}
  .settings-textarea:focus {{ outline: 1px solid var(--link); }}
  .settings-btn-apply {{
    margin-top: 8px;
    padding: 6px 16px;
    background: var(--link);
    color: var(--bg);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
  }}
  .settings-btn-apply:hover {{ opacity: 0.9; }}
  .settings-error {{
    color: #f44;
    font-size: 12px;
    margin-top: 4px;
    display: none;
  }}
  .settings-ref-link {{
    font-size: 12px;
    margin-bottom: 8px;
  }}
  .settings-ref-link a {{ color: var(--link); }}
  .settings-slider-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }}
  .settings-slider-row label {{
    font-size: 13px;
    min-width: 100px;
  }}
  .settings-slider-row input[type="range"] {{
    flex: 1;
  }}
  .settings-slider-row .slider-value {{
    font-size: 12px;
    color: var(--file-path);
    min-width: 50px;
    text-align: right;
  }}
  .settings-color-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }}
  .settings-color-row label {{
    font-size: 13px;
    min-width: 28px;
  }}
  .heading-color-select {{
    flex: 1;
    padding: 4px 6px;
    font-size: 13px;
    color: var(--fg);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    outline: none;
  }}
  .heading-color-select:focus {{ border-color: var(--link); }}
  .color-swatch {{
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    vertical-align: middle;
    margin-right: 4px;
    border: 1px solid rgba(255,255,255,0.2);
  }}
  /* minimap */
  .minimap {{
    position: fixed;
    top: 0;
    right: 0;
    width: var(--minimap-width);
    height: 100vh;
    background: var(--code-bg);
    border-left: 1px solid var(--border);
    overflow: hidden;
    z-index: 500;
    cursor: pointer;
  }}
  .minimap-content {{
    position: absolute;
    top: 0;
    left: 0;
    transform-origin: top left;
    pointer-events: none;
  }}
  .minimap-viewport {{
    position: absolute;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    pointer-events: none;
    min-height: 10px;
  }}
  /* スリムで背景に溶け込むスクロールバー（WebKit + Firefox） */
  * {{ scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.18) transparent; }}
  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.16); border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.30); }}
  ::-webkit-scrollbar-corner {{ background: transparent; }}
  /* TOC */
  .toc {{
    position: fixed;
    top: 0;
    left: 0;
    width: var(--toc-width);
    height: 100vh;
    background: var(--code-bg);
    border-right: 1px solid var(--border);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 12px 8px 20px;
    z-index: 500;
    font-size: 13px;
    box-sizing: border-box;
    transform: translateX(-100%);
    transition: transform 0.18s ease;
  }}
  .toc.open {{ transform: translateX(0); }}
  /* パネル領域: 残り高さを占有してスクロール（単独表示モードはここが縦スクロール） */
  .toc-panes {{ flex: 1 1 auto; min-height: 0; overflow-y: auto; overflow-x: hidden; }}
  /* 両方表示（分割）モード: 左Files / 右Outline を横並び・個別スクロール。境界はドラッグ可。 */
  .toc.split .toc-panes {{ display: flex; flex-direction: row; overflow: hidden; }}
  .toc.split .toc-pane {{ min-width: 0; overflow-y: auto; overflow-x: hidden; display: block !important; }}
  .toc.split #paneFiles {{ order: 0; flex: 0 0 var(--toc-split, 50%); padding-right: 6px; }}
  .toc.split #paneOutline {{ order: 2; flex: 1 1 0; padding-left: 8px; }}
  .toc-split-resize {{ display: none; }}
  .toc.split .toc-split-resize {{
    display: block;
    order: 1;
    flex: 0 0 5px;
    margin: 0 -2px;
    cursor: col-resize;
    background: var(--border);
    opacity: 0.5;
    z-index: 1;
  }}
  .toc.split .toc-split-resize:hover {{ background: var(--link); opacity: 0.6; }}
  /* モードセレクタ（Files / Outline / Both）。内容が無いボタンはdisabled表示。 */
  .toc-modes {{ display: flex; gap: 2px; margin-bottom: 8px; border-bottom: 1px solid var(--border); }}
  .toc-mode-btn {{
    flex: 1;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--fg);
    opacity: 0.55;
    padding: 6px 4px;
    font-size: 12px;
    cursor: pointer;
  }}
  .toc-mode-btn:hover {{ opacity: 0.85; }}
  .toc-mode-btn.active {{ opacity: 1; color: var(--link); border-bottom-color: var(--link); }}
  .toc-mode-btn:disabled {{ opacity: 0.22; cursor: default; }}
  /* 見切れた項目はホバー時、その行だけ枠をはみ出して全文表示する。
     位置・文字色・サイズを元の行に合わせ、別物でなく「行が右へ続く」ように見せる。 */
  #treeTip {{
    position: fixed;
    z-index: 2000;
    display: none;
    align-items: center;
    box-sizing: border-box;
    /* ホバー時の淡いハイライト(0.06)を code-bg に合成し、行の見た目に揃える */
    background: linear-gradient(rgba(255,255,255,0.06), rgba(255,255,255,0.06)), var(--code-bg);
    color: var(--fg);
    white-space: nowrap;
    pointer-events: none;
    padding-right: 12px;
    border-radius: 0 4px 4px 0;
    box-shadow: 3px 0 10px rgba(0,0,0,0.4);
  }}
  #treeTip.show {{ display: flex; }}
  .toc li {{ margin: 0; }}  /* ツリー行間の隙間（global li margin）を打ち消す */
  /* リサイズハンドル（左サイドバー右端 / ミニマップ左端） */
  .toc-resize {{
    position: fixed;
    top: 0;
    left: var(--toc-width);
    width: 6px;
    height: 100vh;
    margin-left: -3px;
    cursor: col-resize;
    z-index: 600;
    display: none;
  }}
  body.toc-open .toc-resize {{ display: block; }}
  .toc-resize:hover, .minimap-resize:hover {{ background: var(--link); opacity: 0.5; }}
  .minimap-resize {{
    position: fixed;
    top: 0;
    right: var(--minimap-width);
    width: 6px;
    height: 100vh;
    margin-right: -3px;
    cursor: col-resize;
    z-index: 600;
  }}
  /* アウトラインのリンク専用（#paneOutline限定。Filesの<a.tree-file>に波及させない） */
  #paneOutline a {{
    display: block;
    color: var(--fg);
    text-decoration: none;
    padding: 3px 8px;
    border-left: 2px solid transparent;
    opacity: 0.65;
    line-height: 1.35;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  #paneOutline a:hover {{ opacity: 1; background: rgba(255,255,255,0.04); }}
  #paneOutline a.active {{
    opacity: 1;
    border-left-color: var(--link);
    color: var(--link);
    background: rgba(255,255,255,0.03);
  }}
  #paneOutline .toc-h1 {{ font-weight: 600; }}
  #paneOutline .toc-h2 {{ padding-left: 18px; }}
  #paneOutline .toc-h3 {{ padding-left: 32px; font-size: 12px; }}
  #paneOutline .toc-h4 {{ padding-left: 46px; font-size: 12px; }}
  #paneOutline .toc-h5 {{ padding-left: 60px; font-size: 11px; }}
  #paneOutline .toc-h6 {{ padding-left: 74px; font-size: 11px; }}
  /* モードセレクタ（.toc-modes / .toc-mode-btn）のスタイルは上部にまとめて定義 */
  /* file tree (Files tab) -- 行は全幅・隙間なし、インデントはpadding-leftで均等付与 */
  .toc-tree, .toc-tree ul {{ list-style: none; margin: 0; padding: 0; }}
  .tree-row {{
    display: flex;
    align-items: center;
    gap: 4px;
    margin: 0;
    padding: 4px 8px;
    color: var(--fg);
    text-decoration: none;
    opacity: 0.7;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    overflow: hidden;
    border-left: 2px solid transparent;
    line-height: 1.4;
    box-sizing: border-box;
  }}
  .tree-row:hover {{ opacity: 1; background: rgba(255,255,255,0.06); }}
  .tree-file.active {{
    opacity: 1;
    color: var(--link);
    border-left-color: var(--link);
    background: rgba(255,255,255,0.04);
  }}
  .tree-folder.collapsed > ul {{ display: none; }}
  .tree-name {{ flex: 1 1 0; min-width: 0; overflow: hidden; text-overflow: ellipsis; }}
  /* ファイル/フォルダ識別アイコン（SVG, currentColor追従）。フォルダは見出し色で強調。 */
  .tree-icon {{ flex: 0 0 16px; display: inline-flex; align-items: center; justify-content: center; margin-right: 3px; }}
  .tree-icon svg {{ display: block; }}
  /* フォルダアイコンで開閉を表現: 展開時=開いたフォルダ、折り畳み時=閉じたフォルダ */
  .tree-icon .icon-closed {{ display: none; }}
  .tree-folder.collapsed > .tree-row .tree-icon .icon-open {{ display: none; }}
  .tree-folder.collapsed > .tree-row .tree-icon .icon-closed {{ display: block; }}
  .tree-folder > .tree-row .tree-icon {{ color: var(--heading); opacity: 0.9; }}
  .tree-file .tree-icon {{ color: var(--fg); opacity: 0.55; }}
  .tree-file.active .tree-icon {{ color: var(--link); opacity: 1; }}
  /* 開いているファイルを含むフォルダは、折り畳み時に行をハイライト（active fileと同調）。
     展開中はファイル自体が見えるので無印。has-activeは保持され、折り畳みトグルだけで反応。 */
  .tree-folder.collapsed.has-active > .tree-row {{
    opacity: 1;
    color: var(--link);
    border-left-color: var(--link);
    background: rgba(255,255,255,0.04);
  }}
  .tree-folder.collapsed.has-active > .tree-row .tree-icon {{ color: var(--link); opacity: 1; }}
  /* ファイルが多いフォルダ: 直下のファイル群を固定高スクロール枠にまとめる。
     左マージン（枠の左端=上位フォルダのx位置）はJSでインラインに設定する。 */
  .tree-filebox {{
    max-height: 240px;
    overflow-y: auto;
    overflow-x: hidden;
    margin: 2px 4px 4px 0;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: rgba(255,255,255,0.02);
  }}
  .tree-filebox > ul {{ padding: 2px 0; }}
  /* ツリーのインデントとガイド: フォルダの中身（ネストした子ul）を1段下げ、
     各項目に縦＋横の点線コネクタ（├）を描く。最後の項目は縦線を行の中央(13px)で
     止めて └ にする。縦線はli高さ100%なので折り畳み時も子の有無に自動追従する。 */
  .toc-tree ul.tree-children {{ margin-left: 16px; }}
  .tree-children > li {{ position: relative; }}
  .tree-children > li::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    border-left: 1px dotted var(--border);
  }}
  .tree-children > li:last-child::before {{ height: 13px; }}  /* └: 行中央で止める */
  .tree-children > li::after {{
    content: "";
    position: absolute;
    left: 0;
    top: 13px;
    width: 9px;
    border-top: 1px dotted var(--border);
  }}
  .toc-toggle {{
    position: fixed;
    top: 10px;
    left: 10px;
    width: 30px;
    height: 30px;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--code-bg);
    color: var(--fg);
    font-size: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0.5;
    transition: opacity 0.2s, left 0.18s ease, top 0.18s ease;
  }}
  .toc-toggle:hover {{ opacity: 1; }}
  /* サイドバーを開いている時: ハンバーガーはサイドバー右端の外側（Splitボタンの右）へ。
     普段は非表示で、サイドバーかボタン自身にマウスを近づけた時だけ半透明で出す。 */
  body.toc-open .toc-toggle {{
    top: 8px;
    left: var(--toc-width);
    opacity: 0;
    pointer-events: none;
  }}
  body.toc-open .toc.toggle-near ~ .toc-toggle,
  body.toc-open .toc-toggle:hover {{ opacity: 0.4; pointer-events: auto; }}
  body.toc-open .toc-toggle:hover {{ opacity: 0.85; }}
  body.toc-open {{ margin-left: calc(var(--toc-width) + 20px); margin-right: 20px; }}
  /* Edit mode */
  .edit-btn {{
    position: fixed;
    bottom: 20px;
    right: calc(var(--minimap-width) + 66px);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--code-bg);
    color: var(--fg);
    font-size: 15px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0.6;
    transition: opacity 0.2s;
  }}
  .edit-btn:hover {{ opacity: 1; }}
  .settings-btn {{ right: calc(var(--minimap-width) + 20px); }}
  .edit-panel {{
    display: none;
    position: fixed;
    inset: 0;
    z-index: 3000;
    background: var(--bg);
    padding: 40px 40px 80px 40px;
    box-sizing: border-box;
  }}
  body.editing .edit-panel {{ display: block; }}
  body.editing .edit-controls {{ display: flex; }}
  .edit-textarea {{
    width: 100%;
    height: 100%;
    background: var(--code-bg);
    color: var(--fg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 14px 16px;
    font-family: Consolas, Menlo, monospace;
    font-size: 14px;
    line-height: 1.5;
    resize: none;
    box-sizing: border-box;
    outline: none;
    tab-size: 4;
  }}
  .edit-textarea:focus {{ border-color: var(--link); }}
  .edit-controls {{
    display: none;
    position: fixed;
    bottom: 20px;
    right: 20px;
    gap: 8px;
    z-index: 3001;
    align-items: center;
  }}
  .edit-controls .edit-status {{
    font-size: 12px;
    color: var(--file-path);
    margin-right: 8px;
  }}
  .edit-controls button {{
    padding: 8px 16px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--code-bg);
    color: var(--fg);
    cursor: pointer;
    font-size: 13px;
  }}
  .edit-controls button.save {{
    background: var(--link);
    color: var(--bg);
    border-color: var(--link);
  }}
  .edit-controls button:hover {{ opacity: 0.9; }}
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

// コードブロックのシンタックスハイライト用テーマ（highlight.js）。
// /static/hljs/<key>.min.css を id="hljsTheme" のlinkに差し替えて切替える。
// アプリ（ページ）テーマとは独立。背景は --code-bg に統一しトークン色のみ反映。
const CODE_THEMES = [
  {{ key: "github-dark", name: "GitHub Dark" }},
  {{ key: "atom-one-dark", name: "Atom One Dark" }},
  {{ key: "tokyo-night-dark", name: "Tokyo Night Dark" }},
  {{ key: "monokai", name: "Monokai" }},
  {{ key: "dracula", name: "Dracula" }},
  {{ key: "nord", name: "Nord" }},
  {{ key: "vs2015", name: "VS 2015" }},
  {{ key: "a11y-dark", name: "a11y Dark" }},
];
const DEFAULT_CODE_THEME = "github-dark";
function applyCodeTheme(key) {{
  const link = document.getElementById("hljsTheme");
  if (link) link.href = "/static/hljs/" + key + ".min.css";
}}

function applyTheme(keyOrTheme) {{
  const theme = (typeof keyOrTheme === "string") ? THEMES[keyOrTheme] : keyOrTheme;
  if (!theme) return;
  const root = document.documentElement;
  Object.keys(theme).forEach(k => {{
    if (k.startsWith("--")) root.style.setProperty(k, theme[k]);
  }});
  // テーマ本来のfg（明度調整の基準。dim結果が累積しないよう素の値を保持）
  if (theme["--fg"]) root.style.setProperty("--fg-theme", theme["--fg"]);
}}

const savedTheme = localStorage.getItem("md-preview-theme") || "monokai";
if (savedTheme === "custom") {{
  const ct = localStorage.getItem("md-preview-custom-theme");
  if (ct) applyTheme(JSON.parse(ct));
}} else {{
  applyTheme(savedTheme);
}}
const savedCodeTheme = localStorage.getItem("md-preview-code-theme") || DEFAULT_CODE_THEME;
applyCodeTheme(savedCodeTheme);
// ユーザーが上書きした色。テーマ切替で上書きされるため、テーマ適用のたびに再適用する。
function _parseColor(s) {{
  s = (s || "").trim();
  if (s[0] === "#") {{
    if (s.length === 4) s = "#" + s[1]+s[1]+s[2]+s[2]+s[3]+s[3];
    if (s.length >= 7) return [parseInt(s.slice(1,3),16), parseInt(s.slice(3,5),16), parseInt(s.slice(5,7),16)];
  }}
  const m = s.match(/rgba?\\(([^)]+)\\)/);
  if (m) {{ const p = m[1].split(",").map(x => parseFloat(x)); return [p[0]||0, p[1]||0, p[2]||0]; }}
  return null;
}}
// RGBをf倍して暗くする（まぶしさ低減の明度調整。f=1で無変化）
function _dim(color, f) {{
  const rgb = _parseColor(color);
  if (!rgb) return color;
  const d = c => Math.max(0, Math.min(255, Math.round(c * f)));
  return "rgb(" + d(rgb[0]) + "," + d(rgb[1]) + "," + d(rgb[2]) + ")";
}}
// 本文色: 選択色（無ければテーマの--fg）を明度(brightness%)で暗くして適用
function applyBodyColor() {{
  const base = localStorage.getItem("md-preview--fg");
  const b = parseInt(localStorage.getItem("md-preview-fg-brightness") || "100", 10);
  const root = document.documentElement;
  const themeFg = getComputedStyle(root).getPropertyValue("--fg-theme").trim();
  if (!base && b >= 100) {{
    // 既定に戻す: テーマの素のfgを再適用（過去のdim結果を残さない）
    if (themeFg) root.style.setProperty("--fg", themeFg);
    return;
  }}
  // 基準色は「選択色」または「テーマの素のfg」。現在の--fg（dim済みかも）は使わない＝累積防止。
  const baseColor = base || themeFg || getComputedStyle(root).getPropertyValue("--fg").trim();
  root.style.setProperty("--fg", _dim(baseColor, b / 100));
}}
function applyUserColors() {{
  ["--h1-color","--h2-color","--h3-color","--h4-color"].forEach(k => {{
    const v = localStorage.getItem("md-preview-" + k);
    if (v) document.documentElement.style.setProperty(k, v);
  }});
  applyBodyColor();
}}
applyUserColors();
const savedListMargin = localStorage.getItem("md-preview-list-margin");
if (savedListMargin) document.documentElement.style.setProperty("--list-margin", savedListMargin + "px");
const savedMaxWidth = localStorage.getItem("md-preview-max-width");
</script>
</head>
<body>
<script>
if (savedMaxWidth) document.body.style.maxWidth = savedMaxWidth + "px";
if (localStorage.getItem("md-preview-toc-open") === "1") document.body.classList.add("toc-open");
const savedMinimapWidth = localStorage.getItem("md-preview-minimap-width");
if (savedMinimapWidth) document.documentElement.style.setProperty("--minimap-width", savedMinimapWidth + "px");
const savedTocWidth = localStorage.getItem("md-preview-toc-width");
if (savedTocWidth) document.documentElement.style.setProperty("--toc-width", savedTocWidth + "px");
const savedTocSplit = parseFloat(localStorage.getItem("md-preview-toc-split-pct"));
if (savedTocSplit >= 10 && savedTocSplit <= 90) {{
  document.documentElement.style.setProperty("--toc-split", savedTocSplit + "%");
}}
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
    <div class="settings-section-title">Import Colors</div>
    <div class="settings-ref-link"><a href="https://iterm2colorschemes.com/" target="_blank" rel="noopener">iTerm2 Color Schemes</a> — .itermcolors plist format</div>
    <textarea class="settings-textarea" id="colorImportArea" placeholder="Paste .itermcolors XML here..."></textarea>
    <div class="settings-error" id="colorImportError"></div>
    <button class="settings-btn-apply" id="colorImportBtn">Apply</button>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Text Color</div>
    <div class="settings-color-row"><label>Body</label><select class="heading-color-select" id="fgColor"></select></div>
    <div class="settings-slider-row"><label>Brightness</label><input type="range" id="fgBrightness" min="40" max="100" value="100" step="5"><span class="slider-value" id="fgBrightnessValue">100%</span></div>
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
<div class="file-path" id="filePathEl">{filepath}</div>
<main id="mdContent">
{content}
</main>
<script>
// 現在表示中ファイルの状態（シームレス切替で書き換わる）。各モジュールはここを参照する。
window.__md = {{ path: "{filepath_js}", hash: "{content_hash}" }};

// --- コンテンツ後処理: mermaid変換 + hljs + ミニマップ再構築（切替時に再実行） ---
function __processContent() {{
  document.querySelectorAll("#mdContent pre > code.language-mermaid").forEach((code) => {{
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = code.textContent;
    code.parentElement.replaceWith(div);
  }});
  document.querySelectorAll("#mdContent pre code").forEach((el) => {{
    try {{ delete el.dataset.highlighted; hljs.highlightElement(el); }} catch(e) {{}}
  }});
  if (window.mermaid) {{
    if (!window.__mermaidInit) {{
      mermaid.initialize({{ startOnLoad: false, theme: "dark", securityLevel: "loose" }});
      window.__mermaidInit = true;
    }}
    // 描画は非同期。完了後にミニマップを構築する（描画途中の cloneNode 競合で
    // 先頭の図(sequence等)が壊れるのを防ぐ）。
    mermaid.run({{ querySelector: "#mdContent .mermaid" }}).finally(function() {{
      if (window._rebuildMinimap) window._rebuildMinimap();
    }});
  }} else {{
    if (window._rebuildMinimap) window._rebuildMinimap();
  }}
}}
window.__processContent = __processContent;
__processContent();

// --- Settings modal ---
(function() {{
  const modal = document.getElementById("settingsModal");
  const overlay = document.getElementById("settingsOverlay");
  const btn = document.getElementById("settingsBtn");
  const closeBtn = document.getElementById("settingsClose");
  const themeSelect = document.getElementById("themeSelect");
  let currentTheme = localStorage.getItem("md-preview-theme") || "monokai";

  function openModal() {{
    modal.classList.add("open");
    overlay.classList.add("open");
  }}
  function closeModal() {{
    modal.classList.remove("open");
    overlay.classList.remove("open");
  }}

  btn.addEventListener("click", (e) => {{
    e.stopPropagation();
    openModal();
  }});
  closeBtn.addEventListener("click", closeModal);
  overlay.addEventListener("click", closeModal);

  function renderThemeSelect() {{
    themeSelect.innerHTML = "";
    const allThemes = Object.assign({{}}, THEMES);
    const customTheme = localStorage.getItem("md-preview-custom-theme");
    if (customTheme) {{
      allThemes.custom = Object.assign({{ name: "Custom" }}, JSON.parse(customTheme));
    }}
    Object.entries(allThemes).forEach(([key, theme]) => {{
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = theme.name;
      if (key === currentTheme) opt.selected = true;
      themeSelect.appendChild(opt);
    }});
  }}

  themeSelect.addEventListener("change", () => {{
    const key = themeSelect.value;
    currentTheme = key;
    const customTheme = localStorage.getItem("md-preview-custom-theme");
    applyTheme(key === "custom" && customTheme ? JSON.parse(customTheme) : THEMES[key]);
    applyUserColors();   // テーマで上書きされた--fg等のユーザー色を再適用（維持）
    buildFgSelect();     // 本文色セレクトの既定表示を新テーマに合わせて更新
    localStorage.setItem("md-preview-theme", key);
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});

  renderThemeSelect();

  // --- Code theme (syntax highlighting) ---
  const codeThemeSelect = document.getElementById("codeThemeSelect");
  function renderCodeThemeSelect() {{
    codeThemeSelect.innerHTML = "";
    const cur = localStorage.getItem("md-preview-code-theme") || DEFAULT_CODE_THEME;
    CODE_THEMES.forEach(t => {{
      const opt = document.createElement("option");
      opt.value = t.key;
      opt.textContent = t.name;
      if (t.key === cur) opt.selected = true;
      codeThemeSelect.appendChild(opt);
    }});
  }}
  codeThemeSelect.addEventListener("change", () => {{
    const key = codeThemeSelect.value;
    applyCodeTheme(key);
    localStorage.setItem("md-preview-code-theme", key);
  }});
  renderCodeThemeSelect();

  // --- Color import ---
  const colorImportArea = document.getElementById("colorImportArea");
  const colorImportBtn = document.getElementById("colorImportBtn");
  const colorImportError = document.getElementById("colorImportError");

  function parseItermColors(xmlStr) {{
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlStr, "text/xml");
    if (doc.querySelector("parsererror")) throw new Error("Invalid XML");
    const dict = doc.querySelector("plist > dict");
    if (!dict) throw new Error("Invalid plist structure");

    const colors = {{}};
    const keys = dict.children;
    for (let i = 0; i < keys.length; i++) {{
      if (keys[i].tagName === "key") {{
        const name = keys[i].textContent;
        const val = keys[i+1];
        if (val && val.tagName === "dict") {{
          if (name.includes("(Dark)") || name.includes("(Light)")) continue;
          const entries = val.children;
          const c = {{}};
          for (let j = 0; j < entries.length; j++) {{
            if (entries[j].tagName === "key") {{
              c[entries[j].textContent] = entries[j+1] ? entries[j+1].textContent : "";
            }}
          }}
          const r = parseFloat(c["Red Component"] || 0);
          const g = parseFloat(c["Green Component"] || 0);
          const b = parseFloat(c["Blue Component"] || 0);
          const hex = "#" + [r, g, b].map(v => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
          colors[name] = hex;
        }}
      }}
    }}
    return colors;
  }}

  function lightenColor(hex, amount) {{
    const r = Math.min(255, parseInt(hex.slice(1, 3), 16) + amount);
    const g = Math.min(255, parseInt(hex.slice(3, 5), 16) + amount);
    const b = Math.min(255, parseInt(hex.slice(5, 7), 16) + amount);
    return "#" + [r, g, b].map(v => v.toString(16).padStart(2, "0")).join("");
  }}

  function mapItermToTheme(colors) {{
    const bg = colors["Background Color"] || "#272822";
    const fg = colors["Foreground Color"] || "#d8d8d2";
    const ansi0 = colors["Ansi 0 Color"] || "#1e1f1c";
    const ansi3 = colors["Ansi 3 Color"] || "#d4a76a";
    const ansi4 = colors["Ansi 4 Color"] || "#66c2b5";
    const ansi5 = colors["Ansi 5 Color"] || "#ae9fcc";
    const ansi8 = colors["Ansi 8 Color"] || "#3e3f3a";
    return {{
      name: "Custom",
      "--bg": bg,
      "--fg": fg,
      "--code-bg": ansi0,
      "--border": ansi8,
      "--blockquote-fg": ansi8,
      "--blockquote-border": ansi8,
      "--link": ansi4,
      "--file-path": ansi8,
      "--table-stripe": lightenColor(bg, 10),
      "--heading": ansi3,
      "--accent": ansi5,
    }};
  }}

  colorImportBtn.addEventListener("click", () => {{
    colorImportError.style.display = "none";
    try {{
      const xml = colorImportArea.value.trim();
      if (!xml) throw new Error("Paste .itermcolors XML first");
      const colors = parseItermColors(xml);
      // Save full palette for heading color selects
      localStorage.setItem("md-preview-palette", JSON.stringify(colors));
      const theme = mapItermToTheme(colors);
      localStorage.setItem("md-preview-custom-theme", JSON.stringify(theme));
      localStorage.setItem("md-preview-theme", "custom");
      currentTheme = "custom";
      applyTheme(theme);
      renderThemeSelect();
      // Auto-assign heading colors from palette (skip bg-like colors)
      const bg = colors["Background Color"] || "";
      const candidates = Object.entries(colors)
        .filter(([name, hex]) => !name.includes("Background") && hex !== bg
          && !name.includes("Ansi 0") && !name.includes("Ansi 8"))
        .map(([name, hex]) => hex);
      // Pick 4 distinct colors spread across the palette
      const unique = [...new Set(candidates)];
      const pick = (i) => unique.length > 0 ? unique[i % unique.length] : theme["--heading"];
      const step = Math.max(1, Math.floor(unique.length / 4));
      const hVars = ["--h1-color", "--h2-color", "--h3-color", "--h4-color"];
      hVars.forEach((v, i) => {{
        const c = pick(i * step);
        document.documentElement.style.setProperty(v, c);
        localStorage.setItem("md-preview-" + v, c);
      }});
      buildHeadingSelects();
      applyUserColors();   // 本文色(--fg)のユーザー上書きを維持
      buildFgSelect();
      if (window._rebuildMinimap) window._rebuildMinimap();
    }} catch (e) {{
      colorImportError.textContent = e.message;
      colorImportError.style.display = "block";
    }}
  }});

  // --- Heading color settings ---
  const headingDefs = [
    {{ id: "h1Color", cssVar: "--h1-color" }},
    {{ id: "h2Color", cssVar: "--h2-color" }},
    {{ id: "h3Color", cssVar: "--h3-color" }},
    {{ id: "h4Color", cssVar: "--h4-color" }},
  ];

  function getPalette() {{
    // Build palette from current theme's CSS variables + imported palette
    const palette = [];
    const imported = localStorage.getItem("md-preview-palette");
    if (imported) {{
      try {{
        const p = JSON.parse(imported);
        Object.entries(p).forEach(([name, hex]) => {{
          palette.push({{ name: name, hex: hex }});
        }});
      }} catch(e) {{}}
    }}
    if (palette.length === 0) {{
      // Fallback: extract from current theme
      const root = getComputedStyle(document.documentElement);
      const vars = ["--fg","--heading","--link","--accent","--blockquote-fg","--border","--bg","--code-bg"];
      const names = ["Foreground","Heading","Link","Accent","Muted","Border","Background","Code BG"];
      vars.forEach((v, i) => {{
        const val = root.getPropertyValue(v).trim();
        if (val) palette.push({{ name: names[i], hex: val }});
      }});
    }}
    return palette;
  }}

  function buildHeadingSelects() {{
    const palette = getPalette();
    headingDefs.forEach(h => {{
      const sel = document.getElementById(h.id);
      const saved = localStorage.getItem("md-preview-" + h.cssVar);
      sel.innerHTML = "";
      palette.forEach(p => {{
        const opt = document.createElement("option");
        opt.value = p.hex;
        opt.textContent = p.name + " (" + p.hex + ")";
        opt.style.color = p.hex;
        if (saved && saved === p.hex) opt.selected = true;
        sel.appendChild(opt);
      }});
      // If saved value not in palette, still apply it
      if (saved) {{
        sel.value = saved;
        document.documentElement.style.setProperty(h.cssVar, saved);
      }}
      sel.style.color = sel.value;  // 設定中の色をセレクト自体の文字色に反映
    }});
  }}

  headingDefs.forEach(h => {{
    document.getElementById(h.id).addEventListener("change", (e) => {{
      const val = e.target.value;
      document.documentElement.style.setProperty(h.cssVar, val);
      localStorage.setItem("md-preview-" + h.cssVar, val);
      e.target.style.color = val;  // セレクトの表示色も追従
    }});
  }});

  buildHeadingSelects();

  // --- Body text color (--fg) --- Hxと同様にパレットから選択。テーマ切替後も維持。
  const fgSelect = document.getElementById("fgColor");
  function buildFgSelect() {{
    const palette = getPalette();
    const saved = localStorage.getItem("md-preview--fg");
    const cur = saved || getComputedStyle(document.documentElement).getPropertyValue("--fg").trim();
    fgSelect.innerHTML = "";
    let matched = false;
    palette.forEach(p => {{
      const opt = document.createElement("option");
      opt.value = p.hex;
      opt.textContent = p.name + " (" + p.hex + ")";
      opt.style.color = p.hex;
      if (cur && cur.toLowerCase() === p.hex.toLowerCase()) {{ opt.selected = true; matched = true; }}
      fgSelect.appendChild(opt);
    }});
    // パレットに無い現在値（カスタム）も選べるよう末尾に追加
    if (cur && !matched) {{
      const opt = document.createElement("option");
      opt.value = cur;
      opt.textContent = "Current (" + cur + ")";
      opt.style.color = cur;
      opt.selected = true;
      fgSelect.appendChild(opt);
    }}
    fgSelect.style.color = fgSelect.value;  // 設定中の色をセレクト自体の文字色に反映
  }}
  fgSelect.addEventListener("change", (e) => {{
    localStorage.setItem("md-preview--fg", e.target.value);  // 選択色（base）を保存
    applyBodyColor();                                        // 明度を反映して適用
    e.target.style.color = e.target.value;                   // セレクトの表示色も追従
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});
  buildFgSelect();

  // 本文色の明度（まぶしさ調整）スライダー
  const fgBrightness = document.getElementById("fgBrightness");
  const fgBrightnessValue = document.getElementById("fgBrightnessValue");
  const savedFgB = parseInt(localStorage.getItem("md-preview-fg-brightness") || "100", 10);
  fgBrightness.value = savedFgB;
  fgBrightnessValue.textContent = savedFgB + "%";
  fgBrightness.addEventListener("input", (e) => {{
    const v = parseInt(e.target.value, 10);
    fgBrightnessValue.textContent = v + "%";
    localStorage.setItem("md-preview-fg-brightness", v);
    applyBodyColor();
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});

  document.getElementById("shuffleHeadingBtn").addEventListener("click", () => {{
    const palette = getPalette();
    // Exclude dark/bg-like colors
    const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
    const candidates = palette.filter(p => p.hex !== bg
      && !p.name.includes("Background") && !p.name.includes("Ansi 0 ") && !p.name.includes("Ansi 8 "));
    if (candidates.length === 0) return;
    // Shuffle and pick 4
    const shuffled = candidates.slice().sort(() => Math.random() - 0.5);
    const hVars = ["--h1-color", "--h2-color", "--h3-color", "--h4-color"];
    hVars.forEach((v, i) => {{
      const c = shuffled[i % shuffled.length].hex;
      document.documentElement.style.setProperty(v, c);
      localStorage.setItem("md-preview-" + v, c);
    }});
    buildHeadingSelects();
  }});

  // --- Layout settings ---
  const listMarginSlider = document.getElementById("listMarginSlider");
  const listMarginValue = document.getElementById("listMarginValue");
  const maxWidthSlider = document.getElementById("maxWidthSlider");
  const maxWidthValue = document.getElementById("maxWidthValue");
  const minimapWidthSlider = document.getElementById("minimapWidthSlider");
  const minimapWidthValue = document.getElementById("minimapWidthValue");

  const savedListMargin = localStorage.getItem("md-preview-list-margin");
  const savedMaxWidth = localStorage.getItem("md-preview-max-width");
  const savedMinimapWidth = localStorage.getItem("md-preview-minimap-width");

  if (savedListMargin !== null) {{
    listMarginSlider.value = savedListMargin;
    listMarginValue.textContent = savedListMargin + "px";
  }}
  if (savedMaxWidth !== null) {{
    maxWidthSlider.value = savedMaxWidth;
    maxWidthValue.textContent = savedMaxWidth + "px";
  }}
  if (savedMinimapWidth !== null) {{
    minimapWidthSlider.value = savedMinimapWidth;
    minimapWidthValue.textContent = savedMinimapWidth + "px";
  }}

  listMarginSlider.addEventListener("input", () => {{
    const val = listMarginSlider.value;
    listMarginValue.textContent = val + "px";
    document.documentElement.style.setProperty("--list-margin", val + "px");
    localStorage.setItem("md-preview-list-margin", val);
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});

  maxWidthSlider.addEventListener("input", () => {{
    const val = maxWidthSlider.value;
    maxWidthValue.textContent = val + "px";
    document.body.style.maxWidth = val + "px";
    localStorage.setItem("md-preview-max-width", val);
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});

  minimapWidthSlider.addEventListener("input", () => {{
    const val = minimapWidthSlider.value;
    minimapWidthValue.textContent = val + "px";
    document.documentElement.style.setProperty("--minimap-width", val + "px");
    localStorage.setItem("md-preview-minimap-width", val);
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});
}})();

// --- Resize handles: 左サイドバー幅 / ミニマップ幅 ---
(function() {{
  function clamp(v, lo, hi) {{ return Math.max(lo, Math.min(hi, v)); }}
  function startDrag(handle, onMove, onEnd) {{
    if (!handle) return;
    handle.addEventListener("mousedown", (e) => {{
      e.preventDefault();
      e.stopPropagation();
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";
      function mv(ev) {{ onMove(ev.clientX); }}
      function up() {{
        document.removeEventListener("mousemove", mv);
        document.removeEventListener("mouseup", up);
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
        if (onEnd) onEnd();
      }}
      document.addEventListener("mousemove", mv);
      document.addEventListener("mouseup", up);
    }});
  }}

  // 左サイドバー: 左端=0 なので clientX がそのまま幅
  startDrag(document.getElementById("tocResize"), (x) => {{
    const w = clamp(Math.round(x), 150, 900);
    document.documentElement.style.setProperty("--toc-width", w + "px");
    localStorage.setItem("md-preview-toc-width", w);
  }});

  // 両方表示（分割）時の Files/Outline 境界: Files側の幅を「割合(%)」で保持する。
  // ％にすることでサイドバー幅やウインドウサイズの変化に動的に追従する。
  startDrag(document.getElementById("tocSplitResize"), (x) => {{
    const panes = document.getElementById("tocPanes");
    const r = panes.getBoundingClientRect();
    if (r.width <= 0) return;
    const pct = clamp(((x - r.left) / r.width) * 100, 15, 85);
    document.documentElement.style.setProperty("--toc-split", pct.toFixed(2) + "%");
    localStorage.setItem("md-preview-toc-split-pct", pct.toFixed(2));
  }});

  // ミニマップ: 右端固定なので 幅 = 画面幅 - clientX。設定スライダーとも同期。
  const mmSlider = document.getElementById("minimapWidthSlider");
  const mmValue = document.getElementById("minimapWidthValue");
  startDrag(document.getElementById("minimapResize"), (x) => {{
    const w = clamp(Math.round(window.innerWidth - x), 60, 400);
    document.documentElement.style.setProperty("--minimap-width", w + "px");
    localStorage.setItem("md-preview-minimap-width", w);
    if (mmSlider) mmSlider.value = w;
    if (mmValue) mmValue.textContent = w + "px";
    if (window._updateMinimapScale) window._updateMinimapScale();  // ドラッグ中は軽量な再スケールのみ
  }}, () => {{ if (window._rebuildMinimap) window._rebuildMinimap(); }});  // 終了時に再構築
}})();

(function() {{
  setInterval(async () => {{
    if (document.body.classList.contains("editing")) return;
    try {{
      const res = await fetch("/hash?path=" + encodeURIComponent(window.__md.path));
      const data = await res.json();
      if (data.hash && data.hash !== window.__md.hash) {{
        window.__md.hash = data.hash;
        if (window.__reloadCurrent) window.__reloadCurrent();
        else location.reload();
      }}
    }} catch(e) {{}}
  }}, 1000);
}})();

// --- Edit mode ---
(function() {{
  const btn = document.getElementById("editBtn");
  const panel = document.getElementById("editPanel");
  const textarea = document.getElementById("editTextarea");
  const controls = document.getElementById("editControls");
  const cancelBtn = document.getElementById("editCancelBtn");
  const saveBtn = document.getElementById("editSaveBtn");
  const status = document.getElementById("editStatus");
  let originalText = "";

  function setStatus(msg) {{
    status.textContent = msg || "";
  }}

  function isDirty() {{
    return textarea.value !== originalText;
  }}

  // 他ファイルへ切替える前に呼ばれる。未保存なら確認し、OKなら編集を抜ける。
  window.__editGuard = function() {{
    if (document.body.classList.contains("editing")) {{
      if (isDirty() && !confirm("Discard unsaved changes?")) return false;
      exit(true);
    }}
    return true;
  }};

  async function enter() {{
    setStatus("Loading...");
    try {{
      const res = await fetch("/content?path=" + encodeURIComponent(window.__md.path));
      if (!res.ok) throw new Error("HTTP " + res.status);
      const text = await res.text();
      originalText = text;
      textarea.value = text;
      document.body.classList.add("editing");
      setStatus("");
      textarea.focus();
    }} catch(e) {{
      setStatus("Load failed: " + e.message);
      alert("Load failed: " + e.message);
    }}
  }}

  function exit(force) {{
    if (!force && isDirty() && !confirm("Discard unsaved changes?")) return;
    document.body.classList.remove("editing");
    setStatus("");
  }}

  async function save() {{
    setStatus("Saving...");
    try {{
      const res = await fetch("/save?path=" + encodeURIComponent(window.__md.path), {{
        method: "POST",
        headers: {{ "Content-Type": "text/plain; charset=utf-8" }},
        body: textarea.value,
      }});
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json().catch(() => null);
      if (data && data.hash) window.__md.hash = data.hash;
      originalText = textarea.value;
      setStatus("Saved");
      document.body.classList.remove("editing");
      if (window.__reloadCurrent) window.__reloadCurrent();
      else location.reload();
    }} catch(e) {{
      setStatus("Save failed: " + e.message);
      alert("Save failed: " + e.message);
    }}
  }}

  btn.addEventListener("click", enter);
  cancelBtn.addEventListener("click", () => exit(false));
  saveBtn.addEventListener("click", save);

  document.addEventListener("keydown", (e) => {{
    const editing = document.body.classList.contains("editing");
    if (e.ctrlKey && e.key.toLowerCase() === "s" && editing) {{
      e.preventDefault();
      save();
    }} else if (e.key === "Escape" && editing) {{
      e.preventDefault();
      exit(false);
    }} else if (e.ctrlKey && e.key.toLowerCase() === "e" && !editing) {{
      e.preventDefault();
      enter();
    }}
  }});

  textarea.addEventListener("keydown", (e) => {{
    if (e.key === "Tab") {{
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      if (start === end) {{
        textarea.setRangeText("    ", start, end, "end");
      }} else {{
        // Indent selected lines
        const before = textarea.value.substring(0, start);
        const lineStart = before.lastIndexOf("\\n") + 1;
        const selected = textarea.value.substring(lineStart, end);
        const indented = selected.replace(/^/gm, "    ");
        textarea.setRangeText(indented, lineStart, end, "end");
      }}
    }}
  }});

  window.addEventListener("beforeunload", (e) => {{
    if (document.body.classList.contains("editing") && isDirty()) {{
      e.preventDefault();
      e.returnValue = "";
    }}
  }});
}})();

// --- Sidebar: Outline + Files ---
(function() {{
  const toc = document.getElementById("toc");
  const tocBtn = document.getElementById("tocToggle");
  const modeBar = document.getElementById("tocModes");
  const modeFiles = document.getElementById("modeFiles");
  const modeOutline = document.getElementById("modeOutline");
  const modeBoth = document.getElementById("modeBoth");
  const paneOutline = document.getElementById("paneOutline");
  const paneFiles = document.getElementById("paneFiles");
  const tocPanes = document.getElementById("tocPanes");
  const splitResize = document.getElementById("tocSplitResize");
  const mdContent = document.getElementById("mdContent");
  const filePathEl = document.getElementById("filePathEl");

  // ---- Outline (headings) ----
  let links = [];
  let activeLink = null;
  function rebuildOutline() {{
    paneOutline.innerHTML = "";
    links = [];
    activeLink = null;
    mdContent.querySelectorAll("h1,h2,h3,h4,h5,h6").forEach((h, i) => {{
      if (!h.id) h.id = "toc-h-" + i;
      const a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent.trim();
      a.className = "toc-" + h.tagName.toLowerCase();
      a.addEventListener("click", (e) => {{
        e.preventDefault();
        const top = h.getBoundingClientRect().top + window.scrollY - 20;
        window.scrollTo({{ top: top, behavior: "smooth" }});
      }});
      paneOutline.appendChild(a);
      links.push({{ heading: h, link: a }});
    }});
  }}
  function updateActive() {{
    if (!links.length) return;
    const threshold = 80;
    let cur = links[0];
    for (const l of links) {{
      const top = l.heading.getBoundingClientRect().top;
      if (top <= threshold) cur = l;
      else break;
    }}
    if (cur !== activeLink) {{
      if (activeLink) activeLink.link.classList.remove("active");
      activeLink = cur;
      activeLink.link.classList.add("active");
      const lr = activeLink.link.getBoundingClientRect();
      const pr = paneOutline.getBoundingClientRect();
      if (lr.top < pr.top + 40 || lr.bottom > pr.bottom - 20) {{
        activeLink.link.scrollIntoView({{ block: "center", behavior: "auto" }});
      }}
    }}
  }}
  window.addEventListener("scroll", updateActive, {{ passive: true }});

  // ---- 表示モード（files / outline / both） ----
  const savedMode = localStorage.getItem("md-preview-toc-mode");
  let tocMode = (savedMode === "files" || savedMode === "outline" || savedMode === "both")
    ? savedMode
    : (savedMode === "split" ? "both" : "both");  // 旧値からの移行（tabs/split→both）
  // モードを適用。内容が無いモードは選べないが、セレクタ自体は常時表示して必ず復帰可能にする。
  function applyTocMode() {{
    const hasOutline = links.length > 0;
    const hasFiles = paneFiles.childElementCount > 0;
    modeFiles.disabled = !hasFiles;
    modeOutline.disabled = !hasOutline;
    modeBoth.disabled = !(hasFiles && hasOutline);
    // 選択モードは保持しつつ、表示可能な範囲へ補正（内容が戻れば選択が復帰する）
    let m = tocMode;
    if (m === "both" && !(hasFiles && hasOutline)) m = hasFiles ? "files" : "outline";
    if (m === "files" && !hasFiles) m = hasOutline ? "outline" : "files";
    if (m === "outline" && !hasOutline) m = hasFiles ? "files" : "outline";
    const split = (m === "both");
    toc.classList.toggle("split", split);
    paneFiles.style.display = (split || m === "files") ? "" : "none";
    paneOutline.style.display = (split || m === "outline") ? "" : "none";
    modeFiles.classList.toggle("active", m === "files");
    modeOutline.classList.toggle("active", m === "outline");
    modeBoth.classList.toggle("active", m === "both");
    modeBar.style.display = (hasOutline || hasFiles) ? "" : "none";
  }}
  [modeFiles, modeOutline, modeBoth].forEach(btn => {{
    btn.addEventListener("click", () => {{
      if (btn.disabled) return;
      tocMode = btn.dataset.mode;
      localStorage.setItem("md-preview-toc-mode", tocMode);
      applyTocMode();
      if (window._rebuildMinimap) window._rebuildMinimap();
    }});
  }});

  // ---- 見切れた項目はホバーで即時に全文表示（Files/Outline 共通） ----
  const tip = document.createElement("div");
  tip.id = "treeTip";
  document.body.appendChild(tip);
  function hideTip() {{ tip.classList.remove("show"); }}
  // measureEl: 見切れ判定に使う要素 / posEl: 位置・体裁を合わせる要素
  function showTip(measureEl, posEl, text) {{
    if (!measureEl || !posEl) {{ hideTip(); return; }}
    if (measureEl.scrollWidth <= measureEl.clientWidth + 1) {{ hideTip(); return; }}  // 見切れていなければ出さない
    const r = posEl.getBoundingClientRect();
    const cs = getComputedStyle(posEl);
    // テキスト開始位置（左パディング＋ボーダー分）に正確に合わせ、高さは行に一致させて中央寄せ
    const padL = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.borderLeftWidth) || 0);
    tip.textContent = text;
    tip.style.left = (r.left + padL) + "px";
    tip.style.top = r.top + "px";
    tip.style.height = r.height + "px";
    tip.style.fontSize = cs.fontSize;
    tip.style.fontWeight = cs.fontWeight;
    tip.style.color = cs.color;
    tip.classList.add("show");
  }}
  toc.addEventListener("mouseover", (e) => {{
    const row = e.target.closest(".tree-row");
    if (row) {{
      const nm = row.querySelector(".tree-name");
      if (!nm) {{ hideTip(); return; }}
      // .tree-name が flex item として幅を持てば nm で判定、持てない(幅0=インライン)なら行で判定
      const measure = (nm.clientWidth > 0) ? nm : row;
      showTip(measure, nm, nm.textContent);
      return;
    }}
    const link = e.target.closest("#paneOutline a");
    if (link) {{ showTip(link, link, link.textContent); return; }}
    hideTip();
  }});
  toc.addEventListener("mouseleave", hideTip);
  toc.addEventListener("scroll", hideTip, true);  // スクロールで位置がずれるため隠す
  document.addEventListener("mousedown", hideTip);

  // ---- Open / close ----
  function setOpen(open) {{
    toc.classList.toggle("open", open);
    document.body.classList.toggle("toc-open", open);
    localStorage.setItem("md-preview-toc-open", open ? "1" : "0");
    if (window._rebuildMinimap) window._rebuildMinimap();
  }}
  tocBtn.addEventListener("click", () => setOpen(!toc.classList.contains("open")));
  document.addEventListener("keydown", (e) => {{
    if (e.ctrlKey && e.key === "\\\\") {{
      e.preventDefault();
      setOpen(!toc.classList.contains("open"));
    }}
  }});
  // ハンバーガー近接表示: 開いている時、サイドバー右端から一定範囲内（+56px）に
  // カーソルがあればボタンを出す。サイドバー外のボタンへマウスを移動しても消えない。
  document.addEventListener("mousemove", (e) => {{
    if (!document.body.classList.contains("toc-open")) return;
    const rightEdge = toc.getBoundingClientRect().right;
    toc.classList.toggle("toggle-near", e.clientX <= rightEdge + 56);
  }}, {{ passive: true }});

  // ---- Seamless file load (右ペインのみ差し替え。ツリー状態は維持) ----
  function setActiveFile(abs) {{
    paneFiles.querySelectorAll(".tree-file.active").forEach(a => a.classList.remove("active"));
    paneFiles.querySelectorAll(".tree-file").forEach(a => {{
      if (a.dataset.abs === abs) a.classList.add("active");
    }});
    updateFolderActive();
  }}
  // 開いているファイルの祖先フォルダに has-active を付与（折り畳み時にCSSでハイライト）
  function updateFolderActive() {{
    paneFiles.querySelectorAll(".tree-folder.has-active").forEach(li => li.classList.remove("has-active"));
    const act = paneFiles.querySelector(".tree-file.active");
    if (!act) return;
    let el = act.parentElement;
    while (el && el !== paneFiles) {{
      if (el.classList && el.classList.contains("tree-folder")) el.classList.add("has-active");
      el = el.parentElement;
    }}
  }}
  function loadFile(abs, opts) {{
    opts = opts || {{}};
    if (window.__editGuard && !window.__editGuard()) return;
    const keepScroll = !!opts.keepScroll;
    const prevY = window.scrollY;
    fetch("/render?path=" + encodeURIComponent(abs))
      .then(r => {{ if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }})
      .then(data => {{
        mdContent.innerHTML = data.html;
        if (filePathEl) filePathEl.textContent = abs;
        if (data.title) document.title = data.title;
        window.__md.path = abs;
        window.__md.hash = data.hash;
        if (window.__processContent) window.__processContent();
        rebuildOutline();
        updateActive();
        setActiveFile(abs);
        if (opts.push !== false) {{
          history.pushState({{ path: abs }}, "", "/view?path=" + encodeURIComponent(abs));
        }}
        window.scrollTo(0, keepScroll ? prevY : 0);
      }})
      .catch(() => {{ window.location = "/view?path=" + encodeURIComponent(abs); }});
  }}
  window.__reloadCurrent = function() {{ loadFile(window.__md.path, {{ push: false, keepScroll: true }}); }};
  window.addEventListener("popstate", (e) => {{
    const p = e.state && e.state.path;
    if (p) loadFile(p, {{ push: false }});
  }});

  // ---- Files tree ----
  // インデントとガイド線はネストした子ulのCSS（.tree-children）で表現する。
  const FILE_SCROLL_THRESHOLD = 15; // 直下ファイルがこれを超えたらスクロール枠にまとめる
  // ファイル/フォルダ識別アイコン（Octiconsベースの線画、currentColor追従）
  function treeIcon(kind) {{
    const span = document.createElement("span");
    span.className = "tree-icon";
    if (kind === "folder") {{
      // 開いた/閉じたフォルダの両SVGを入れ、.collapsedクラスでCSSが出し分ける
      span.innerHTML =
        '<svg class="icon-open" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M.513 1.513A1.75 1.75 0 0 1 1.75 1h3.5c.55 0 1.07.26 1.4.7l.9 1.2a.25.25 0 0 0 .2.1H13a1 1 0 0 1 1 1v.5H2.75a.75.75 0 0 0 0 1.5h11.978a1 1 0 0 1 .994 1.117L15 13.25A1.75 1.75 0 0 1 13.25 15H1.75A1.75 1.75 0 0 1 0 13.25V2.75c0-.464.184-.91.513-1.237Z"/></svg>'
        + '<svg class="icon-closed" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75Z"/></svg>';
    }} else {{
      span.innerHTML = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Zm6.75.062V4.25c0 .138.112.25.25.25h2.688a.252.252 0 0 0-.011-.013l-2.914-2.914a.272.272 0 0 0-.013-.011Z"/></svg>';
    }}
    return span;
  }}
  function buildTree(files) {{
    const root = {{ dirs: {{}}, files: [] }};
    files.forEach(f => {{
      const parts = f.rel.split("/");
      let node = root;
      for (let i = 0; i < parts.length - 1; i++) {{
        const d = parts[i];
        node.dirs[d] = node.dirs[d] || {{ dirs: {{}}, files: [] }};
        node = node.dirs[d];
      }}
      node.files.push({{ name: parts[parts.length - 1], abs: f.abs }});
    }});
    return root;
  }}
  // 現在ファイルへ至るフォルダパスを展開状態にするための集合
  function pathDirs(rel) {{
    const parts = rel.split("/");
    const set = {{}};
    let acc = "";
    for (let i = 0; i < parts.length - 1; i++) {{
      acc = acc ? acc + "/" + parts[i] : parts[i];
      set[acc] = true;
    }}
    return set;
  }}
  function renderInto(ul, node, prefix, depth, openDirs) {{
    Object.keys(node.dirs).sort().forEach(name => {{
      const full = prefix ? prefix + "/" + name : name;
      const li = document.createElement("li");
      li.className = "tree-folder";
      if (!openDirs[full]) li.classList.add("collapsed");
      const row = document.createElement("div");
      row.className = "tree-row";
      const nm = document.createElement("span");
      nm.className = "tree-name";
      nm.textContent = name;
      row.appendChild(treeIcon("folder"));
      row.appendChild(nm);
      row.addEventListener("click", () => li.classList.toggle("collapsed"));
      li.appendChild(row);
      const childUl = document.createElement("ul");
      childUl.className = "tree-children";
      renderInto(childUl, node.dirs[name], full, depth + 1, openDirs);
      li.appendChild(childUl);
      ul.appendChild(li);
    }});
    const sortedFiles = node.files.sort((a, b) => a.name.localeCompare(b.name));
    // 直下ファイルが多い場合は固定高スクロール枠にまとめる
    let fileContainer = ul;
    if (sortedFiles.length > FILE_SCROLL_THRESHOLD) {{
      const boxLi = document.createElement("li");
      const box = document.createElement("div");
      box.className = "tree-filebox";
      const innerUl = document.createElement("ul");
      innerUl.className = "toc-tree";
      box.appendChild(innerUl);
      boxLi.appendChild(box);
      ul.appendChild(boxLi);
      fileContainer = innerUl;
    }}
    sortedFiles.forEach(f => {{
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.className = "tree-row tree-file";
      a.href = "/view?path=" + encodeURIComponent(f.abs);
      a.dataset.abs = f.abs;
      const nm = document.createElement("span");
      nm.className = "tree-name";
      nm.textContent = f.name;
      a.appendChild(treeIcon("file"));
      a.appendChild(nm);
      if (f.abs === window.__md.path) a.classList.add("active");
      a.addEventListener("click", (e) => {{ e.preventDefault(); loadFile(f.abs, {{ push: true }}); }});
      li.appendChild(a);
      fileContainer.appendChild(li);
    }});
  }}

  function finalize() {{
    const hasOutline = links.length > 0;
    const hasFiles = paneFiles.childElementCount > 0;
    applyTocMode();
    tocBtn.style.display = (hasOutline || hasFiles) ? "" : "none";
    const savedOpen = localStorage.getItem("md-preview-toc-open") === "1";
    setOpen(savedOpen && (hasOutline || hasFiles));
  }}

  // 初期化: アウトライン構築 → 一度確定 → ファイル一覧（git）を一度だけ取得して確定
  rebuildOutline();
  updateActive();
  finalize();
  history.replaceState({{ path: window.__md.path }}, "", location.href);
  fetch("/files?path=" + encodeURIComponent(window.__md.path))
    .then(r => r.json())
    .then(data => {{
      const files = (data && data.files) || [];
      if (files.length > 1) {{
        const tree = buildTree(files);
        const cur = files.find(f => f.abs === window.__md.path);
        const openDirs = cur ? pathDirs(cur.rel) : {{}};
        const rootUl = document.createElement("ul");
        rootUl.className = "toc-tree";
        renderInto(rootUl, tree, "", 0, openDirs);
        paneFiles.appendChild(rootUl);
        updateFolderActive();
        const act = paneFiles.querySelector(".tree-file.active");
        if (act) act.scrollIntoView({{ block: "center" }});
      }}
      finalize();
    }})
    .catch(() => {{}});
}})();

// --- Minimap ---
(function() {{
  const minimap = document.getElementById("minimap");
  const minimapContent = document.getElementById("minimapContent");
  const minimapViewport = document.getElementById("minimapViewport");
  var scaleX, contentOriginalHeight;

  function buildMinimapContent() {{
    minimapContent.innerHTML = "";
    const contentSource = document.querySelector(".file-path");
    let el = contentSource;
    while (el) {{
      if (el !== minimap && el.id !== "settingsBtn" && el.id !== "settingsModal" && el.id !== "settingsOverlay"
          && el.id !== "toc" && el.id !== "tocToggle") {{
        minimapContent.appendChild(el.cloneNode(true));
      }}
      el = el.nextElementSibling;
    }}
  }}

  function applyScale() {{
    const contentWidth = parseInt(document.body.style.maxWidth) || 800;
    minimapContent.style.width = contentWidth + "px";
    // Reset transform and minimap height so we measure against the full viewport
    minimapContent.style.transform = "none";
    minimap.style.height = "";
    contentOriginalHeight = minimapContent.scrollHeight;
    // Scale to fit: use whichever is smaller — width-fit or height-fit
    const minimapWidth = minimap.clientWidth;
    const scaleByWidth = minimapWidth / contentWidth;
    const minimapH = minimap.clientHeight;
    const scaleByHeight = minimapH / contentOriginalHeight;
    scaleX = Math.min(scaleByWidth, scaleByHeight);
    minimapContent.style.transform = "scale(" + scaleX + ")";
    // Shrink minimap to scaled content height when content fits,
    // so the viewport indicator can reach the bottom at max scroll.
    const scaledContentH = contentOriginalHeight * scaleX;
    if (scaledContentH < minimapH) {{
      minimap.style.height = scaledContentH + "px";
    }}
  }}

  // 未処理の mermaid 図がある間は初期構築を遅延し、mermaid.run().finally() 内の
  // _rebuildMinimap() に任せる（描画途中の clone 競合を避ける）。
  if (!(window.mermaid && document.querySelector(".mermaid:not([data-processed])"))) {{
    buildMinimapContent();
    applyScale();
  }}

  window._rebuildMinimap = function() {{ buildMinimapContent(); applyScale(); updateViewport(); }};
  window._updateMinimapScale = function() {{ applyScale(); updateViewport(); }};

  function updateViewport() {{
    const docHeight = document.documentElement.scrollHeight;
    const viewHeight = window.innerHeight;
    const scrollTop = window.scrollY;
    const maxDocScroll = docHeight - viewHeight;
    const minimapH = minimap.clientHeight;
    const scaledContentH = contentOriginalHeight * scaleX;

    // Viewport indicator size in scaled pixels
    const vpHeight = Math.max(10, (viewHeight / docHeight) * scaledContentH);

    if (scaledContentH <= minimapH) {{
      // Entire document fits in minimap — no minimap scrolling
      minimapContent.style.top = "0px";
      const vpTop = maxDocScroll > 0 ? (scrollTop / maxDocScroll) * (scaledContentH - vpHeight) : 0;
      minimapViewport.style.top = Math.max(0, vpTop) + "px";
      minimapViewport.style.height = vpHeight + "px";
    }} else {{
      // Document overflows minimap — scroll minimap proportionally
      const scrollFraction = maxDocScroll > 0 ? scrollTop / maxDocScroll : 0;
      const maxContentOffset = scaledContentH - minimapH;
      const contentOffset = scrollFraction * maxContentOffset;
      // top is in pre-transform coords, so divide by scale
      minimapContent.style.top = -(contentOffset / scaleX) + "px";

      const vpTop = scrollFraction * (minimapH - vpHeight);
      minimapViewport.style.top = Math.max(0, vpTop) + "px";
      minimapViewport.style.height = vpHeight + "px";
    }}
  }}

  window.addEventListener("scroll", updateViewport);
  window.addEventListener("resize", function() {{ applyScale(); updateViewport(); }});
  updateViewport();

  // Click/drag to scroll — clicked position becomes viewport center
  function scrollToMinimapPos(clientY) {{
    const rect = minimap.getBoundingClientRect();
    const y = clientY - rect.top;
    const minimapH = minimap.clientHeight;
    const scaledContentH = contentOriginalHeight * scaleX;
    const docHeight = document.documentElement.scrollHeight;
    const viewHeight = window.innerHeight;
    const maxDocScroll = docHeight - viewHeight;

    // Map click position to document fraction
    var docFraction;
    if (scaledContentH <= minimapH) {{
      docFraction = scaledContentH > 0 ? y / scaledContentH : 0;
    }} else {{
      docFraction = y / minimapH;
    }}
    // Scroll so the clicked position is at the center of the viewport
    const targetScroll = docFraction * docHeight - viewHeight / 2;
    window.scrollTo({{ top: Math.max(0, Math.min(targetScroll, maxDocScroll)), behavior: "instant" }});
  }}

  minimap.addEventListener("mousedown", function(e) {{
    e.preventDefault();
    scrollToMinimapPos(e.clientY);
    function onDrag(ev) {{
      scrollToMinimapPos(ev.clientY);
    }}
    function onUp() {{
      document.removeEventListener("mousemove", onDrag);
      document.removeEventListener("mouseup", onUp);
    }}
    document.addEventListener("mousemove", onDrag);
    document.addEventListener("mouseup", onUp);
  }});
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
    # 走査ルート: gitリポジトリならトップ階層、無ければ開いたファイルのフォルダ
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
    try:
        return _scan_dir_markdown(scan_root)
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
                "title": Path(filepath).name,
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
