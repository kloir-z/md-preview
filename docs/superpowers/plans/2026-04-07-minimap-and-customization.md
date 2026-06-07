# ミニマップ + カスタマイズパネル Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Markdownプレビューにミニマップ（CSS Transform方式）とカスタマイズモーダル（テーマ選択・カラーインポート・レイアウト設定）を追加する。

**Architecture:** すべての変更は `md_server.py` の `HTML_TEMPLATE` 文字列内（HTML/CSS/JS）のみ。サーバー側Python変更なし。HTML_TEMPLATEはPython `.format()` を使うため、JSの中括弧は `{{` `}}` でエスケープが必要。

**Tech Stack:** HTML/CSS/JS（vanilla）、DOMParser（XML plist解析）、localStorage

# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）

---

## File Structure

- **Modify:** `md_server.py` — `HTML_TEMPLATE` 文字列のみ変更。以下のセクションを追加/変更:
  - `<style>` — ミニマップCSS、モーダルCSS、レイアウトCSS変数
  - `<head>` 内 `<script>` — 早期設定適用ロジック拡張
  - `<body>` — ミニマップHTML、モーダルHTML（既存の settings-panel を置き換え）
  - `<body>` 末尾 `<script>` — ミニマップJS、モーダルJS、カラーインポートJS

---

### Task 1: ミニマップ — CSS + HTML構造

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: ミニマップCSSを `<style>` に追加**

`md_server.py` の `HTML_TEMPLATE` 内、`.theme-item .check {{ ... }}` の後（155行目付近）に以下を追加:

```css
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
    transform-origin: top left;
    pointer-events: none;
    width: 800px;
    overflow: hidden;
  }}
  .minimap-viewport {{
    position: absolute;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    pointer-events: none;
    min-height: 10px;
  }}
```

- [ ] **Step 2: ミニマップHTMLを `<body>` に追加**

`md_server.py` の `HTML_TEMPLATE` 内、`<body>` 開始タグ直後（238行目付近）に以下を追加:

```html
<div class="minimap" id="minimap">
  <div class="minimap-content" id="minimapContent"></div>
  <div class="minimap-viewport" id="minimapViewport"></div>
</div>
```

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: add minimap HTML structure and CSS"
```

---

### Task 2: ミニマップ — コンテンツクローン + スクロール同期

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: ミニマップJS初期化コードを追加**

`HTML_TEMPLATE` 末尾の `</script>` 直前（ポーリング処理の後、299行目付近）に以下のIIFEを追加:

```javascript
// --- Minimap ---
(function() {{
  const minimap = document.getElementById("minimap");
  const minimapContent = document.getElementById("minimapContent");
  const minimapViewport = document.getElementById("minimapViewport");

  // Clone body content into minimap
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

  buildMinimapContent();

  // Calculate scale to fit content width into minimap width
  const scale = 80 / 800;
  minimapContent.style.transform = "scale(" + scale + ")";

  // Update viewport indicator position on scroll
  function updateViewport() {{
    const docHeight = document.documentElement.scrollHeight;
    const viewHeight = window.innerHeight;
    const scrollTop = window.scrollY;
    const minimapHeight = minimap.clientHeight;
    const contentScaledHeight = minimapContent.scrollHeight * scale;
    const effectiveHeight = Math.min(minimapHeight, contentScaledHeight);

    const vpTop = (scrollTop / docHeight) * effectiveHeight;
    const vpHeight = (viewHeight / docHeight) * effectiveHeight;

    minimapViewport.style.top = vpTop + "px";
    minimapViewport.style.height = vpHeight + "px";
  }}

  window.addEventListener("scroll", updateViewport);
  window.addEventListener("resize", updateViewport);
  updateViewport();
}})();
```

- [ ] **Step 2: サーバーを再起動して動作確認**

```bash
# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）
```

ブラウザでMarkdownファイルを開き、右端にミニマップが表示されていること、スクロールでビューポートインジケーターが動くことを確認。

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: add minimap content cloning and scroll sync"
```

---

### Task 3: ミニマップ — クリック/ドラッグ操作

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: クリック/ドラッグ処理をミニマップIIFEに追加**

Task 2で追加したミニマップIIFE内の `updateViewport();` の直後、`}})();` の直前に以下を追加:

```javascript
  // Click to scroll
  function scrollToMinimapPos(clientY) {{
    const rect = minimap.getBoundingClientRect();
    const y = clientY - rect.top;
    const contentScaledHeight = minimapContent.scrollHeight * scale;
    const effectiveHeight = Math.min(minimap.clientHeight, contentScaledHeight);
    const ratio = y / effectiveHeight;
    const docHeight = document.documentElement.scrollHeight;
    const viewHeight = window.innerHeight;
    const targetScroll = ratio * docHeight - viewHeight / 2;
    window.scrollTo({{ top: targetScroll, behavior: "instant" }});
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
```

- [ ] **Step 2: サーバーを再起動して動作確認**

```bash
# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）
```

ミニマップをクリック→その位置にスクロール。ドラッグ→スクロール追従を確認。

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: add minimap click and drag scrolling"
```

---

### Task 4: モーダル — CSS + HTML構造（既存パネル置き換え）

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: 既存の `.settings-panel` 関連CSSを削除し、モーダルCSSで置き換え**

`HTML_TEMPLATE` 内の以下のCSS（`.settings-panel` から `.theme-item .check` まで、124〜155行目）を削除:

```css
  .settings-panel {
    ...
  }
  .settings-panel.open { display: block; }
  .settings-panel-title { ... }
  .theme-item { ... }
  .theme-item:hover { ... }
  .theme-item.active { ... }
  .theme-item .check { ... }
```

代わりに以下のモーダルCSSを挿入:

```css
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
  .theme-item {{
    padding: 6px 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--fg);
    border-radius: 4px;
  }}
  .theme-item:hover {{ background: var(--bg); }}
  .theme-item.active {{ color: var(--link); }}
  .theme-item .check {{ width: 16px; text-align: center; }}
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
```

- [ ] **Step 2: 既存の settings-panel HTMLを削除し、モーダルHTMLで置き換え**

`HTML_TEMPLATE` 内の以下のHTML（240〜242行目付近）を削除:

```html
<div class="settings-panel" id="settingsPanel">
  <div class="settings-panel-title">Theme</div>
</div>
```

代わりに以下を挿入:

```html
<div class="settings-overlay" id="settingsOverlay"></div>
<div class="settings-modal" id="settingsModal">
  <div class="settings-modal-header">
    <h3>Settings</h3>
    <button class="settings-close" id="settingsClose">&times;</button>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Theme</div>
    <div id="themeList"></div>
  </div>
  <div class="settings-section">
    <div class="settings-section-title">Import Colors</div>
    <div class="settings-ref-link"><a href="https://iterm2colorschemes.com/" target="_blank" rel="noopener">iTerm2 Color Schemes</a> — .itermcolors plist format</div>
    <textarea class="settings-textarea" id="colorImportArea" placeholder="Paste .itermcolors XML here..."></textarea>
    <div class="settings-error" id="colorImportError"></div>
    <button class="settings-btn-apply" id="colorImportBtn">Apply</button>
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
```

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: replace settings popup with modal UI"
```

---

### Task 5: モーダル — テーマ選択ロジック移行

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: 既存のテーマパネルJS IIFEを削除し、モーダルJSで置き換え**

`HTML_TEMPLATE` 末尾の `<script>` 内、`// --- Theme settings panel ---` から始まるIIFE全体（249〜284行目付近）を削除し、以下で置き換え:

```javascript
// --- Settings modal ---
(function() {{
  const modal = document.getElementById("settingsModal");
  const overlay = document.getElementById("settingsOverlay");
  const btn = document.getElementById("settingsBtn");
  const closeBtn = document.getElementById("settingsClose");
  const themeList = document.getElementById("themeList");
  let currentTheme = localStorage.getItem("md-preview-theme") || "monokai";

  function openModal() {{
    modal.classList.add("open");
    overlay.classList.add("open");
    renderThemeList();
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

  function renderThemeList() {{
    themeList.innerHTML = "";
    const allThemes = Object.assign({{}}, THEMES);
    const customTheme = localStorage.getItem("md-preview-custom-theme");
    if (customTheme) {{
      allThemes.custom = Object.assign({{ name: "Custom" }}, JSON.parse(customTheme));
    }}
    Object.entries(allThemes).forEach(([key, theme]) => {{
      const div = document.createElement("div");
      div.className = "theme-item" + (key === currentTheme ? " active" : "");
      div.innerHTML = '<span class="check">' + (key === currentTheme ? "&#10003;" : "") + "</span>" + theme.name;
      div.addEventListener("click", () => {{
        currentTheme = key;
        applyTheme(key === "custom" && customTheme ? JSON.parse(customTheme) : THEMES[key]);
        localStorage.setItem("md-preview-theme", key);
        renderThemeList();
      }});
      themeList.appendChild(div);
    }});
  }}

  renderThemeList();
```

この関数は閉じないでおく（Task 6, 7 でコードを追加してからIIFEを閉じる）。

- [ ] **Step 2: サーバーを再起動して動作確認**

```bash
# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）
```

歯車ボタンクリック→モーダル表示→テーマ切替→×ボタンとオーバーレイクリックで閉じるを確認。

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: migrate theme selection to modal with open/close logic"
```

---

### Task 6: カラーインポート — .itermcolors XMLパーサー

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: カラーインポート処理をモーダルIIFE内に追加**

Task 5で追加した `renderThemeList();` の直後に以下を追加:

```javascript
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
          // Skip (Dark) and (Light) variants
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
      const theme = mapItermToTheme(colors);
      localStorage.setItem("md-preview-custom-theme", JSON.stringify(theme));
      localStorage.setItem("md-preview-theme", "custom");
      currentTheme = "custom";
      applyTheme(theme);
      renderThemeList();
    }} catch (e) {{
      colorImportError.textContent = e.message;
      colorImportError.style.display = "block";
    }}
  }});
```

- [ ] **Step 2: `applyTheme` 関数を更新してオブジェクト直接受け取りに対応**

`HTML_TEMPLATE` の `<head>` 内の `applyTheme` 関数（225〜232行目付近）を以下に置き換え:

```javascript
function applyTheme(themeOrKey) {{
  const theme = (typeof themeOrKey === "string") ? THEMES[themeOrKey] : themeOrKey;
  if (!theme) return;
  const root = document.documentElement;
  Object.keys(theme).forEach(k => {{
    if (k.startsWith("--")) root.style.setProperty(k, theme[k]);
  }});
}}
```

- [ ] **Step 3: `<head>` のテーマ早期適用でcustomテーマに対応**

`HTML_TEMPLATE` の `<head>` 内の早期適用コード（234〜236行目付近）を以下に置き換え:

```javascript
const savedTheme = localStorage.getItem("md-preview-theme") || "monokai";
if (savedTheme === "custom") {{
  const ct = localStorage.getItem("md-preview-custom-theme");
  if (ct) applyTheme(JSON.parse(ct));
}} else {{
  applyTheme(savedTheme);
}}
```

- [ ] **Step 4: サーバーを再起動して動作確認**

```bash
# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）
```

モーダルのImport ColorsテキストエリアにiTerm2 plist XMLを貼り付け→Apply→テーマが変わることを確認。ページリロード後も維持されることを確認。

- [ ] **Step 5: コミット**

```bash
git add md_server.py
git commit -m "feat: add .itermcolors import with XML parsing and color mapping"
```

---

### Task 7: レイアウト設定 — 箇条書きマージン + 最大横幅

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: レイアウト設定JSをモーダルIIFE内に追加**

Task 6で追加したコードの直後に以下を追加:

```javascript
  // --- Layout settings ---
  const listMarginSlider = document.getElementById("listMarginSlider");
  const listMarginValue = document.getElementById("listMarginValue");
  const maxWidthSlider = document.getElementById("maxWidthSlider");
  const maxWidthValue = document.getElementById("maxWidthValue");

  // Load saved values
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
    document.body.style.setProperty("--list-margin", val + "px");
    localStorage.setItem("md-preview-list-margin", val);
  }});

  maxWidthSlider.addEventListener("input", () => {{
    const val = maxWidthSlider.value;
    maxWidthValue.textContent = val + "px";
    document.body.style.maxWidth = val + "px";
    localStorage.setItem("md-preview-max-width", val);
  }});
```

そしてIIFEを閉じる:

```javascript
}})();
```

- [ ] **Step 2: CSS変数 `--list-margin` を追加してリストスタイルに適用**

`HTML_TEMPLATE` の `:root` ブロック（39〜51行目付近）に以下を追加:

```css
    --list-margin: 16px;
```

さらに `<style>` 内に以下を追加:

```css
  li {{ margin-bottom: var(--list-margin); }}
```

- [ ] **Step 3: `<head>` の早期適用スクリプトにレイアウト設定を追加**

Task 6で更新した早期適用コードの直後に以下を追加:

```javascript
const savedListMargin = localStorage.getItem("md-preview-list-margin");
if (savedListMargin) document.documentElement.style.setProperty("--list-margin", savedListMargin + "px");
const savedMaxWidth = localStorage.getItem("md-preview-max-width");
```

そして `<body>` タグにインラインスタイルを追加:

`<body>` を以下に変更:

```html
<body>
<script>
if (savedMaxWidth) document.body.style.maxWidth = savedMaxWidth + "px";
</script>
```

注: `savedMaxWidth` は `<head>` のスクリプトで定義済みなので `<body>` 直後のスクリプトから参照可能。

- [ ] **Step 4: サーバーを再起動して動作確認**

```bash
# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）
```

モーダルのLayoutセクションでスライダーを動かし、箇条書きマージンと最大横幅がリアルタイムに変わることを確認。リロード後も維持されることを確認。

- [ ] **Step 5: IIFEが正しく閉じていることを確認し、コミット**

```bash
git add md_server.py
git commit -m "feat: add layout settings (list margin, max width) with persistence"
```

---

### Task 8: 統合確認 + クリーンアップ

**Files:**
- Modify: `md_server.py:29-302` (HTML_TEMPLATE)

- [ ] **Step 1: ミニマップのリビルドをテーマ変更時にトリガー**

テーマ切替やカラーインポートでミニマップの色を即座に反映させるため、ミニマップIIFE内の `buildMinimapContent` をグローバル関数に変更:

ミニマップIIFEの `function buildMinimapContent()` の直前に以下を追加:

```javascript
  window._rebuildMinimap = function() {{ buildMinimapContent(); }};
```

モーダルIIFE内のテーマ切替処理（`div.addEventListener("click", ...)`内）で `applyTheme` 呼び出しの後に追加:

```javascript
        if (window._rebuildMinimap) window._rebuildMinimap();
```

同様にカラーインポートの `applyTheme(theme);` の後にも追加:

```javascript
      if (window._rebuildMinimap) window._rebuildMinimap();
```

- [ ] **Step 2: サーバーを再起動して全機能を統合テスト**

```bash
# 起動中のサーバープロセスを再起動して反映（pythonw md_server.py を停止 → 再度起動）
```

確認項目:
1. ミニマップ表示 — 右端にコンテンツ縮小表示
2. ミニマップ操作 — クリック/ドラッグでスクロール
3. モーダル開閉 — 歯車→モーダル、×/オーバーレイで閉じる
4. テーマ切替 — テーマ選択→色変更→ミニマップも追従
5. カラーインポート — .itermcolors貼り付け→Apply→適用
6. レイアウト設定 — スライダーでリアルタイム変更
7. 永続化 — ページリロード後もすべて維持

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: integrate minimap rebuild on theme change"
```
