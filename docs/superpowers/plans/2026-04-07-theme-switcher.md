# Theme Switcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ダーク系8テーマをクライアントサイドで切り替えられるようにし、歯車アイコンの設定パネルからテーマを選択・localStorage永続化する。

**Architecture:** `HTML_TEMPLATE` 内にテーマ定義JS・設定パネルUI・テーマ適用ロジックを追加。CSS変数の上書きでテーマ切替。サーバーPythonロジックの変更なし。

**Tech Stack:** Vanilla JS, CSS Custom Properties, localStorage

---

## File Structure

- **Modify:** `md_server.py` — `HTML_TEMPLATE` 内のCSS・JS・HTMLを変更。Python ロジックは変更なし。

変更対象が `HTML_TEMPLATE` 文字列内のみなので、ファイル分割は不要。

---

### Task 1: テーマ定義JSとFOUC防止の早期適用

**Files:**
- Modify: `md_server.py:103` (`</style>` の直後、`</head>` の直前にscriptブロックを挿入)

- [ ] **Step 1: テーマ定義と早期適用スクリプトを追加**

`md_server.py` の `HTML_TEMPLATE` 内、`</style>` と `</head>` の間に以下の `<script>` ブロックを挿入する。

```html
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
```

注意: `HTML_TEMPLATE` は Python の f-string 風テンプレートなので `{{` `}}` がエスケープされた `{` `}` になる。

- [ ] **Step 2: サービス再起動して動作確認**

```powershell
powershell -Command "Start-Process powershell -ArgumentList '-Command','Restart-Service md-preview' -Verb RunAs"
```

ブラウザで `http://localhost:3030/view?path=C:/code/md-preview/README.md` を開き、ページが正常に表示されることを確認。コンソールにJSエラーがないことを確認。

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: add theme definitions and early theme application script"
```

---

### Task 2: 設定パネルUI（HTML + CSS）

**Files:**
- Modify: `md_server.py` — `HTML_TEMPLATE` 内の `<style>` セクションにCSS追加、`<body>` 直後に設定パネルHTMLを追加

- [ ] **Step 1: 設定パネルのCSSを追加**

`md_server.py` の `HTML_TEMPLATE` 内、`li input[type="checkbox"]` ルールの後（`</style>` の前）に以下を追加:

```css
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
```

- [ ] **Step 2: 設定パネルのHTMLを追加**

`HTML_TEMPLATE` 内の `<body>` 直後（`<div class="file-path">` の前）に以下を追加:

```html
<button class="settings-btn" id="settingsBtn" title="Settings">&#9881;</button>
<div class="settings-panel" id="settingsPanel">
  <div class="settings-panel-title">Theme</div>
</div>
```

- [ ] **Step 3: サービス再起動して動作確認**

```powershell
powershell -Command "Start-Process powershell -ArgumentList '-Command','Restart-Service md-preview' -Verb RunAs"
```

ブラウザで確認。右下に歯車ボタンが表示されることを確認（まだ動作しない）。

- [ ] **Step 4: コミット**

```bash
git add md_server.py
git commit -m "feat: add settings panel UI (HTML + CSS)"
```

---

### Task 3: 設定パネルのJSロジック

**Files:**
- Modify: `md_server.py` — `HTML_TEMPLATE` 内の末尾 `<script>` セクションに設定パネルロジックを追加

- [ ] **Step 1: テーマ切替ロジックを追加**

`HTML_TEMPLATE` 内の末尾 `<script>` ブロック（`hljs.highlightAll();` の後、ポーリング処理の前）に以下を追加:

```js
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
```

- [ ] **Step 2: サービス再起動して全機能を動作確認**

```powershell
powershell -Command "Start-Process powershell -ArgumentList '-Command','Restart-Service md-preview' -Verb RunAs"
```

ブラウザで確認:
1. 歯車クリックでパネルが開く
2. テーマをクリックすると即座に配色が変わる
3. 現在のテーマにチェックマークが付く
4. パネル外クリックで閉じる
5. ページリロード後もテーマが維持される
6. 別のmdファイルを開いても同じテーマが適用される

- [ ] **Step 3: コミット**

```bash
git add md_server.py
git commit -m "feat: add theme switching logic with localStorage persistence"
```

---

### Task 4: 最終確認とプッシュ

- [ ] **Step 1: 全テーマの目視確認**

ブラウザで8テーマすべてに切り替え、以下を確認:
- 背景・文字色・リンク色・見出し色が適切に変わる
- コードブロックが読みやすい
- テーブルのストライプが機能している
- blockquoteの色が視認できる

- [ ] **Step 2: プッシュ**

```bash
git push
```
