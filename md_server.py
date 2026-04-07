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
    --h1-color: var(--heading);
    --h2-color: var(--heading);
    --h3-color: var(--heading);
    --h4-color: var(--heading);
    --accent: #ae9fcc;
    --list-margin: 16px;
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
    width: 80px;
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

function applyTheme(keyOrTheme) {{
  const theme = (typeof keyOrTheme === "string") ? THEMES[keyOrTheme] : keyOrTheme;
  if (!theme) return;
  const root = document.documentElement;
  Object.keys(theme).forEach(k => {{
    if (k.startsWith("--")) root.style.setProperty(k, theme[k]);
  }});
}}

const savedTheme = localStorage.getItem("md-preview-theme") || "monokai";
if (savedTheme === "custom") {{
  const ct = localStorage.getItem("md-preview-custom-theme");
  if (ct) applyTheme(JSON.parse(ct));
}} else {{
  applyTheme(savedTheme);
}}
["--h1-color","--h2-color","--h3-color","--h4-color"].forEach(k => {{
  const v = localStorage.getItem("md-preview-" + k);
  if (v) document.documentElement.style.setProperty(k, v);
}});
const savedListMargin = localStorage.getItem("md-preview-list-margin");
if (savedListMargin) document.documentElement.style.setProperty("--list-margin", savedListMargin + "px");
const savedMaxWidth = localStorage.getItem("md-preview-max-width");
</script>
</head>
<body>
<script>
if (savedMaxWidth) document.body.style.maxWidth = savedMaxWidth + "px";
</script>
<div class="minimap" id="minimap">
  <div class="minimap-content" id="minimapContent"></div>
  <div class="minimap-viewport" id="minimapViewport"></div>
</div>
<button class="settings-btn" id="settingsBtn" title="Settings">&#9881;</button>
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
    <div class="settings-section-title">Import Colors</div>
    <div class="settings-ref-link"><a href="https://iterm2colorschemes.com/" target="_blank" rel="noopener">iTerm2 Color Schemes</a> — .itermcolors plist format</div>
    <textarea class="settings-textarea" id="colorImportArea" placeholder="Paste .itermcolors XML here..."></textarea>
    <div class="settings-error" id="colorImportError"></div>
    <button class="settings-btn-apply" id="colorImportBtn">Apply</button>
  </div>
  <div class="settings-section">
    <div class="settings-section-title" style="display:flex;justify-content:space-between;align-items:center;">Heading Colors <button class="settings-btn-apply" id="shuffleHeadingBtn" style="margin:0;padding:2px 10px;font-size:11px;">Shuffle</button></div>
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
      <input type="range" id="maxWidthSlider" min="600" max="1200" value="800" step="50">
      <span class="slider-value" id="maxWidthValue">800px</span>
    </div>
  </div>
</div>
<div class="file-path">{filepath}</div>
{content}
<script>
hljs.highlightAll();

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
    localStorage.setItem("md-preview-theme", key);
    if (window._rebuildMinimap) window._rebuildMinimap();
  }});

  renderThemeSelect();

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
    }});
  }}

  headingDefs.forEach(h => {{
    document.getElementById(h.id).addEventListener("change", (e) => {{
      const val = e.target.value;
      document.documentElement.style.setProperty(h.cssVar, val);
      localStorage.setItem("md-preview-" + h.cssVar, val);
    }});
  }});

  buildHeadingSelects();

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

  const savedListMargin = localStorage.getItem("md-preview-list-margin");
  const savedMaxWidth = localStorage.getItem("md-preview-max-width");

  if (savedListMargin !== null) {{
    listMarginSlider.value = savedListMargin;
    listMarginValue.textContent = savedListMargin + "px";
  }}
  if (savedMaxWidth !== null) {{
    maxWidthSlider.value = savedMaxWidth;
    maxWidthValue.textContent = savedMaxWidth + "px";
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

// --- Minimap ---
(function() {{
  const minimap = document.getElementById("minimap");
  const minimapContent = document.getElementById("minimapContent");
  const minimapViewport = document.getElementById("minimapViewport");
  const MINIMAP_WIDTH = 80;
  var scaleX, contentOriginalHeight;

  function buildMinimapContent() {{
    minimapContent.innerHTML = "";
    const contentSource = document.querySelector(".file-path");
    let el = contentSource;
    while (el) {{
      if (el !== minimap && el.id !== "settingsBtn" && el.id !== "settingsModal" && el.id !== "settingsOverlay") {{
        minimapContent.appendChild(el.cloneNode(true));
      }}
      el = el.nextElementSibling;
    }}
  }}

  function applyScale() {{
    const contentWidth = parseInt(document.body.style.maxWidth) || 800;
    minimapContent.style.width = contentWidth + "px";
    // Reset transform to measure true height
    minimapContent.style.transform = "none";
    contentOriginalHeight = minimapContent.scrollHeight;
    // Scale to fit: use whichever is smaller — width-fit or height-fit
    const scaleByWidth = MINIMAP_WIDTH / contentWidth;
    const minimapH = minimap.clientHeight;
    const scaleByHeight = minimapH / contentOriginalHeight;
    scaleX = Math.min(scaleByWidth, scaleByHeight);
    minimapContent.style.transform = "scale(" + scaleX + ")";
  }}

  buildMinimapContent();
  applyScale();

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
