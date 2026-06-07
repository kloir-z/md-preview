// 現在表示中ファイルの状態（シームレス切替で書き換わる）。各モジュールはここを参照する。
window.__md = JSON.parse(document.getElementById("md-data").textContent);

// --- コンテンツ後処理: mermaid変換 + hljs + ミニマップ再構築（切替時に再実行） ---
function __processContent() {
  document.querySelectorAll("#mdContent pre > code.language-mermaid").forEach((code) => {
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = code.textContent;
    code.parentElement.replaceWith(div);
  });
  document.querySelectorAll("#mdContent pre code").forEach((el) => {
    try { delete el.dataset.highlighted; hljs.highlightElement(el); } catch(e) {}
  });
  if (window.mermaid) {
    if (!window.__mermaidInit) {
      mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose" });
      window.__mermaidInit = true;
    }
    // 描画は非同期。完了後にミニマップを構築する（描画途中の cloneNode 競合で
    // 先頭の図(sequence等)が壊れるのを防ぐ）。
    mermaid.run({ querySelector: "#mdContent .mermaid" }).finally(function() {
      if (window.__ensureBottomRoom) window.__ensureBottomRoom();  // 図の描画後に余白を再算定
      if (window._rebuildMinimap) window._rebuildMinimap();
    });
  } else {
    if (window.__ensureBottomRoom) window.__ensureBottomRoom();
    if (window._rebuildMinimap) window._rebuildMinimap();
  }
}
window.__processContent = __processContent;
__processContent();

// --- Settings modal ---
(function() {
  const modal = document.getElementById("settingsModal");
  const overlay = document.getElementById("settingsOverlay");
  const btn = document.getElementById("settingsBtn");
  const closeBtn = document.getElementById("settingsClose");
  const themeSelect = document.getElementById("themeSelect");
  let currentTheme = localStorage.getItem("md-preview-theme") || "monokai";

  function openModal() {
    modal.classList.add("open");
    overlay.classList.add("open");
  }
  function closeModal() {
    modal.classList.remove("open");
    overlay.classList.remove("open");
  }

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    openModal();
  });
  closeBtn.addEventListener("click", closeModal);
  overlay.addEventListener("click", closeModal);

  function renderThemeSelect() {
    themeSelect.innerHTML = "";
    const allThemes = Object.assign({}, THEMES);
    const customTheme = localStorage.getItem("md-preview-custom-theme");
    if (customTheme) {
      allThemes.custom = Object.assign({ name: "Custom" }, JSON.parse(customTheme));
    }
    Object.entries(allThemes).forEach(([key, theme]) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = theme.name;
      if (key === currentTheme) opt.selected = true;
      themeSelect.appendChild(opt);
    });
  }

  themeSelect.addEventListener("change", () => {
    const key = themeSelect.value;
    currentTheme = key;
    const customTheme = localStorage.getItem("md-preview-custom-theme");
    applyTheme(key === "custom" && customTheme ? JSON.parse(customTheme) : THEMES[key]);
    applyUserColors();   // テーマで上書きされた--fg等のユーザー色を再適用（維持）
    buildFgSelect();     // 本文色セレクトの既定表示を新テーマに合わせて更新
    localStorage.setItem("md-preview-theme", key);
    if (window._rebuildMinimap) window._rebuildMinimap();
  });

  renderThemeSelect();

  // --- Code theme (syntax highlighting) ---
  const codeThemeSelect = document.getElementById("codeThemeSelect");
  function renderCodeThemeSelect() {
    codeThemeSelect.innerHTML = "";
    const cur = localStorage.getItem("md-preview-code-theme") || DEFAULT_CODE_THEME;
    CODE_THEMES.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.key;
      opt.textContent = t.name;
      if (t.key === cur) opt.selected = true;
      codeThemeSelect.appendChild(opt);
    });
  }
  codeThemeSelect.addEventListener("change", () => {
    const key = codeThemeSelect.value;
    applyCodeTheme(key);
    localStorage.setItem("md-preview-code-theme", key);
  });
  renderCodeThemeSelect();

  // --- Color import ---
  const colorImportArea = document.getElementById("colorImportArea");
  const colorImportBtn = document.getElementById("colorImportBtn");
  const colorImportError = document.getElementById("colorImportError");

  function parseItermColors(xmlStr) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlStr, "text/xml");
    if (doc.querySelector("parsererror")) throw new Error("Invalid XML");
    const dict = doc.querySelector("plist > dict");
    if (!dict) throw new Error("Invalid plist structure");

    const colors = {};
    const keys = dict.children;
    for (let i = 0; i < keys.length; i++) {
      if (keys[i].tagName === "key") {
        const name = keys[i].textContent;
        const val = keys[i+1];
        if (val && val.tagName === "dict") {
          if (name.includes("(Dark)") || name.includes("(Light)")) continue;
          const entries = val.children;
          const c = {};
          for (let j = 0; j < entries.length; j++) {
            if (entries[j].tagName === "key") {
              c[entries[j].textContent] = entries[j+1] ? entries[j+1].textContent : "";
            }
          }
          const r = parseFloat(c["Red Component"] || 0);
          const g = parseFloat(c["Green Component"] || 0);
          const b = parseFloat(c["Blue Component"] || 0);
          const hex = "#" + [r, g, b].map(v => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
          colors[name] = hex;
        }
      }
    }
    return colors;
  }

  function lightenColor(hex, amount) {
    const r = Math.min(255, parseInt(hex.slice(1, 3), 16) + amount);
    const g = Math.min(255, parseInt(hex.slice(3, 5), 16) + amount);
    const b = Math.min(255, parseInt(hex.slice(5, 7), 16) + amount);
    return "#" + [r, g, b].map(v => v.toString(16).padStart(2, "0")).join("");
  }

  function mapItermToTheme(colors) {
    const bg = colors["Background Color"] || "#272822";
    const fg = colors["Foreground Color"] || "#d8d8d2";
    const ansi0 = colors["Ansi 0 Color"] || "#1e1f1c";
    const ansi3 = colors["Ansi 3 Color"] || "#d4a76a";
    const ansi4 = colors["Ansi 4 Color"] || "#66c2b5";
    const ansi5 = colors["Ansi 5 Color"] || "#ae9fcc";
    const ansi8 = colors["Ansi 8 Color"] || "#3e3f3a";
    return {
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
    };
  }

  colorImportBtn.addEventListener("click", () => {
    colorImportError.style.display = "none";
    try {
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
      hVars.forEach((v, i) => {
        const c = pick(i * step);
        document.documentElement.style.setProperty(v, c);
        localStorage.setItem("md-preview-" + v, c);
      });
      buildHeadingSelects();
      applyUserColors();   // 本文色(--fg)のユーザー上書きを維持
      buildFgSelect();
      if (window._rebuildMinimap) window._rebuildMinimap();
    } catch (e) {
      colorImportError.textContent = e.message;
      colorImportError.style.display = "block";
    }
  });

  // --- Heading color settings ---
  const headingDefs = [
    { id: "h1Color", cssVar: "--h1-color" },
    { id: "h2Color", cssVar: "--h2-color" },
    { id: "h3Color", cssVar: "--h3-color" },
    { id: "h4Color", cssVar: "--h4-color" },
  ];

  function getPalette() {
    // Build palette from current theme's CSS variables + imported palette
    const palette = [];
    const imported = localStorage.getItem("md-preview-palette");
    if (imported) {
      try {
        const p = JSON.parse(imported);
        Object.entries(p).forEach(([name, hex]) => {
          palette.push({ name: name, hex: hex });
        });
      } catch(e) {}
    }
    if (palette.length === 0) {
      // Fallback: extract from current theme
      const root = getComputedStyle(document.documentElement);
      const vars = ["--fg","--heading","--link","--accent","--blockquote-fg","--border","--bg","--code-bg"];
      const names = ["Foreground","Heading","Link","Accent","Muted","Border","Background","Code BG"];
      vars.forEach((v, i) => {
        const val = root.getPropertyValue(v).trim();
        if (val) palette.push({ name: names[i], hex: val });
      });
    }
    return palette;
  }

  function buildHeadingSelects() {
    const palette = getPalette();
    headingDefs.forEach(h => {
      const sel = document.getElementById(h.id);
      const saved = localStorage.getItem("md-preview-" + h.cssVar);
      sel.innerHTML = "";
      palette.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.hex;
        opt.textContent = p.name + " (" + p.hex + ")";
        opt.style.color = p.hex;
        if (saved && saved === p.hex) opt.selected = true;
        sel.appendChild(opt);
      });
      // If saved value not in palette, still apply it
      if (saved) {
        sel.value = saved;
        document.documentElement.style.setProperty(h.cssVar, saved);
      }
      sel.style.color = sel.value;  // 設定中の色をセレクト自体の文字色に反映
    });
  }

  headingDefs.forEach(h => {
    document.getElementById(h.id).addEventListener("change", (e) => {
      const val = e.target.value;
      document.documentElement.style.setProperty(h.cssVar, val);
      localStorage.setItem("md-preview-" + h.cssVar, val);
      e.target.style.color = val;  // セレクトの表示色も追従
    });
  });

  buildHeadingSelects();

  // --- Body text color (--fg) --- Hxと同様にパレットから選択。テーマ切替後も維持。
  const fgSelect = document.getElementById("fgColor");
  function buildFgSelect() {
    const palette = getPalette();
    const saved = localStorage.getItem("md-preview--fg");
    const cur = saved || getComputedStyle(document.documentElement).getPropertyValue("--fg").trim();
    fgSelect.innerHTML = "";
    let matched = false;
    palette.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.hex;
      opt.textContent = p.name + " (" + p.hex + ")";
      opt.style.color = p.hex;
      if (cur && cur.toLowerCase() === p.hex.toLowerCase()) { opt.selected = true; matched = true; }
      fgSelect.appendChild(opt);
    });
    // パレットに無い現在値（カスタム）も選べるよう末尾に追加
    if (cur && !matched) {
      const opt = document.createElement("option");
      opt.value = cur;
      opt.textContent = "Current (" + cur + ")";
      opt.style.color = cur;
      opt.selected = true;
      fgSelect.appendChild(opt);
    }
    fgSelect.style.color = fgSelect.value;  // 設定中の色をセレクト自体の文字色に反映
  }
  fgSelect.addEventListener("change", (e) => {
    localStorage.setItem("md-preview--fg", e.target.value);  // 選択色（base）を保存
    applyBodyColor();                                        // 明度を反映して適用
    e.target.style.color = e.target.value;                   // セレクトの表示色も追従
    if (window._rebuildMinimap) window._rebuildMinimap();
  });
  buildFgSelect();

  // 本文色の明度（まぶしさ調整）スライダー
  const fgBrightness = document.getElementById("fgBrightness");
  const fgBrightnessValue = document.getElementById("fgBrightnessValue");
  const savedFgB = parseInt(localStorage.getItem("md-preview-fg-brightness") || "100", 10);
  fgBrightness.value = savedFgB;
  fgBrightnessValue.textContent = savedFgB + "%";
  fgBrightness.addEventListener("input", (e) => {
    const v = parseInt(e.target.value, 10);
    fgBrightnessValue.textContent = v + "%";
    localStorage.setItem("md-preview-fg-brightness", v);
    applyBodyColor();
    if (window._rebuildMinimap) window._rebuildMinimap();
  });

  document.getElementById("shuffleHeadingBtn").addEventListener("click", () => {
    const palette = getPalette();
    // Exclude dark/bg-like colors
    const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
    const candidates = palette.filter(p => p.hex !== bg
      && !p.name.includes("Background") && !p.name.includes("Ansi 0 ") && !p.name.includes("Ansi 8 "));
    if (candidates.length === 0) return;
    // Shuffle and pick 4
    const shuffled = candidates.slice().sort(() => Math.random() - 0.5);
    const hVars = ["--h1-color", "--h2-color", "--h3-color", "--h4-color"];
    hVars.forEach((v, i) => {
      const c = shuffled[i % shuffled.length].hex;
      document.documentElement.style.setProperty(v, c);
      localStorage.setItem("md-preview-" + v, c);
    });
    buildHeadingSelects();
  });

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

  if (savedListMargin !== null) {
    listMarginSlider.value = savedListMargin;
    listMarginValue.textContent = savedListMargin + "px";
  }
  if (savedMaxWidth !== null) {
    maxWidthSlider.value = savedMaxWidth;
    maxWidthValue.textContent = savedMaxWidth + "px";
  }
  if (savedMinimapWidth !== null) {
    minimapWidthSlider.value = savedMinimapWidth;
    minimapWidthValue.textContent = savedMinimapWidth + "px";
  }

  listMarginSlider.addEventListener("input", () => {
    const val = listMarginSlider.value;
    listMarginValue.textContent = val + "px";
    document.documentElement.style.setProperty("--list-margin", val + "px");
    localStorage.setItem("md-preview-list-margin", val);
    if (window._rebuildMinimap) window._rebuildMinimap();
  });

  maxWidthSlider.addEventListener("input", () => {
    const val = maxWidthSlider.value;
    maxWidthValue.textContent = val + "px";
    document.body.style.maxWidth = val + "px";
    localStorage.setItem("md-preview-max-width", val);
    if (window._rebuildMinimap) window._rebuildMinimap();
  });

  minimapWidthSlider.addEventListener("input", () => {
    const val = minimapWidthSlider.value;
    minimapWidthValue.textContent = val + "px";
    document.documentElement.style.setProperty("--minimap-width", val + "px");
    localStorage.setItem("md-preview-minimap-width", val);
    if (window._rebuildMinimap) window._rebuildMinimap();
  });
})();

// --- Resize handles: 左サイドバー幅 / ミニマップ幅 ---
(function() {
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function startDrag(handle, onMove, onEnd) {
    if (!handle) return;
    handle.addEventListener("mousedown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";
      function mv(ev) { onMove(ev.clientX); }
      function up() {
        document.removeEventListener("mousemove", mv);
        document.removeEventListener("mouseup", up);
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
        if (onEnd) onEnd();
      }
      document.addEventListener("mousemove", mv);
      document.addEventListener("mouseup", up);
    });
  }

  // 左サイドバー: 左端=0 なので clientX がそのまま幅
  startDrag(document.getElementById("tocResize"), (x) => {
    const w = clamp(Math.round(x), 150, 900);
    document.documentElement.style.setProperty("--toc-width", w + "px");
    localStorage.setItem("md-preview-toc-width", w);
  });

  // 両方表示（分割）時の Files/Outline 境界: Files側の幅を「割合(%)」で保持する。
  // ％にすることでサイドバー幅やウインドウサイズの変化に動的に追従する。
  startDrag(document.getElementById("tocSplitResize"), (x) => {
    const panes = document.getElementById("tocPanes");
    const r = panes.getBoundingClientRect();
    if (r.width <= 0) return;
    const pct = clamp(((x - r.left) / r.width) * 100, 15, 85);
    document.documentElement.style.setProperty("--toc-split", pct.toFixed(2) + "%");
    localStorage.setItem("md-preview-toc-split-pct", pct.toFixed(2));
  });

  // ミニマップ: 右端固定なので 幅 = 画面幅 - clientX。設定スライダーとも同期。
  const mmSlider = document.getElementById("minimapWidthSlider");
  const mmValue = document.getElementById("minimapWidthValue");
  startDrag(document.getElementById("minimapResize"), (x) => {
    const w = clamp(Math.round(window.innerWidth - x), 60, 400);
    document.documentElement.style.setProperty("--minimap-width", w + "px");
    localStorage.setItem("md-preview-minimap-width", w);
    if (mmSlider) mmSlider.value = w;
    if (mmValue) mmValue.textContent = w + "px";
    if (window._updateMinimapScale) window._updateMinimapScale();  // ドラッグ中は軽量な再スケールのみ
  }, () => { if (window._rebuildMinimap) window._rebuildMinimap(); });  // 終了時に再構築
})();

(function() {
  setInterval(async () => {
    if (document.body.classList.contains("editing")) return;
    try {
      const res = await fetch("/hash?path=" + encodeURIComponent(window.__md.path));
      const data = await res.json();
      if (data.hash && data.hash !== window.__md.hash) {
        window.__md.hash = data.hash;
        if (window.__reloadCurrent) window.__reloadCurrent();
        else location.reload();
      }
    } catch(e) {}
  }, 1000);
})();

// --- Edit mode ---
(function() {
  const btn = document.getElementById("editBtn");
  const panel = document.getElementById("editPanel");
  const textarea = document.getElementById("editTextarea");
  const controls = document.getElementById("editControls");
  const cancelBtn = document.getElementById("editCancelBtn");
  const saveBtn = document.getElementById("editSaveBtn");
  const status = document.getElementById("editStatus");
  let originalText = "";

  function setStatus(msg) {
    status.textContent = msg || "";
  }

  function isDirty() {
    return textarea.value !== originalText;
  }

  // 他ファイルへ切替える前に呼ばれる。未保存なら確認し、OKなら編集を抜ける。
  window.__editGuard = function() {
    if (document.body.classList.contains("editing")) {
      if (isDirty() && !confirm("Discard unsaved changes?")) return false;
      exit(true);
    }
    return true;
  };

  async function enter() {
    setStatus("Loading...");
    try {
      const res = await fetch("/content?path=" + encodeURIComponent(window.__md.path));
      if (!res.ok) throw new Error("HTTP " + res.status);
      const text = await res.text();
      originalText = text;
      textarea.value = text;
      document.body.classList.add("editing");
      setStatus("");
      textarea.focus();
    } catch(e) {
      setStatus("Load failed: " + e.message);
      alert("Load failed: " + e.message);
    }
  }

  function exit(force) {
    if (!force && isDirty() && !confirm("Discard unsaved changes?")) return;
    document.body.classList.remove("editing");
    setStatus("");
  }

  async function save() {
    setStatus("Saving...");
    try {
      const res = await fetch("/save?path=" + encodeURIComponent(window.__md.path), {
        method: "POST",
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        body: textarea.value,
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json().catch(() => null);
      if (data && data.hash) window.__md.hash = data.hash;
      originalText = textarea.value;
      setStatus("Saved");
      document.body.classList.remove("editing");
      if (window.__reloadCurrent) window.__reloadCurrent();
      else location.reload();
    } catch(e) {
      setStatus("Save failed: " + e.message);
      alert("Save failed: " + e.message);
    }
  }

  btn.addEventListener("click", enter);
  cancelBtn.addEventListener("click", () => exit(false));
  saveBtn.addEventListener("click", save);

  document.addEventListener("keydown", (e) => {
    const editing = document.body.classList.contains("editing");
    if (e.ctrlKey && e.key.toLowerCase() === "s" && editing) {
      e.preventDefault();
      save();
    } else if (e.key === "Escape" && editing) {
      e.preventDefault();
      exit(false);
    } else if (e.ctrlKey && e.key.toLowerCase() === "e" && !editing) {
      e.preventDefault();
      enter();
    }
  });

  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      if (start === end) {
        textarea.setRangeText("    ", start, end, "end");
      } else {
        // Indent selected lines
        const before = textarea.value.substring(0, start);
        const lineStart = before.lastIndexOf("\n") + 1;
        const selected = textarea.value.substring(lineStart, end);
        const indented = selected.replace(/^/gm, "    ");
        textarea.setRangeText(indented, lineStart, end, "end");
      }
    }
  });

  window.addEventListener("beforeunload", (e) => {
    if (document.body.classList.contains("editing") && isDirty()) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
})();

// --- Sidebar: Outline + Files ---
(function() {
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
  function rebuildOutline() {
    paneOutline.innerHTML = "";
    links = [];
    activeLink = null;
    mdContent.querySelectorAll("h1,h2,h3,h4,h5,h6").forEach((h, i) => {
      if (!h.id) h.id = "toc-h-" + i;
      const a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent.trim();
      a.className = "toc-" + h.tagName.toLowerCase();
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const top = h.getBoundingClientRect().top + window.scrollY - 20;
        window.scrollTo({ top: top, behavior: "smooth" });
      });
      paneOutline.appendChild(a);
      links.push({ heading: h, link: a });
    });
  }
  function updateActive() {
    if (!links.length) return;
    const threshold = 80;
    let cur = links[0];
    for (const l of links) {
      const top = l.heading.getBoundingClientRect().top;
      if (top <= threshold) cur = l;
      else break;
    }
    if (cur !== activeLink) {
      if (activeLink) activeLink.link.classList.remove("active");
      activeLink = cur;
      activeLink.link.classList.add("active");
      const lr = activeLink.link.getBoundingClientRect();
      const pr = paneOutline.getBoundingClientRect();
      if (lr.top < pr.top + 40 || lr.bottom > pr.bottom - 20) {
        activeLink.link.scrollIntoView({ block: "center", behavior: "auto" });
      }
    }
  }
  // 末尾付近の見出しは、ページを下まで送ってもビューポート上端の閾値まで上がってこられず
  // （スクロール余地が尽きるため）、updateActive で拾われずハイライトされない。最後の見出しが
  // 上端の閾値に到達できるだけの余白を本文下に足して、全見出しをスクロールで辿れるようにする。
  // 足すのは「最後の見出しを上端に持ってくるのに不足している分」だけ＝余白は最小限。
  function ensureBottomScrollRoom() {
    mdContent.style.paddingBottom = "";  // まず素の高さで測る
    if (!links.length) return;
    const viewH = window.innerHeight;
    const maxScroll = document.documentElement.scrollHeight - viewH;
    if (maxScroll <= 0) return;          // 画面に収まる文書はそのまま（スクロール不要）
    const threshold = 80;                // updateActive と同じ上端閾値
    const last = links[links.length - 1].heading;
    const lastTop = last.getBoundingClientRect().top + window.scrollY;  // 文書上端からの絶対位置
    const extra = (lastTop - threshold) - maxScroll;
    if (extra > 0) mdContent.style.paddingBottom = Math.ceil(extra) + "px";
  }
  window.__ensureBottomRoom = ensureBottomScrollRoom;
  window.addEventListener("scroll", updateActive, { passive: true });
  // ビューポート高が変わると必要な余白も変わる
  window.addEventListener("resize", () => { ensureBottomScrollRoom(); updateActive(); });

  // ---- 表示モード（files / outline / both） ----
  const savedMode = localStorage.getItem("md-preview-toc-mode");
  let tocMode = (savedMode === "files" || savedMode === "outline" || savedMode === "both")
    ? savedMode
    : (savedMode === "split" ? "both" : "both");  // 旧値からの移行（tabs/split→both）
  // モードを適用。内容が無いモードは選べないが、セレクタ自体は常時表示して必ず復帰可能にする。
  function applyTocMode() {
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
  }
  [modeFiles, modeOutline, modeBoth].forEach(btn => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      tocMode = btn.dataset.mode;
      localStorage.setItem("md-preview-toc-mode", tocMode);
      applyTocMode();
      if (window._rebuildMinimap) window._rebuildMinimap();
    });
  });

  // ---- 見切れた項目はホバーで即時に全文表示（Files/Outline 共通） ----
  const tip = document.createElement("div");
  tip.id = "treeTip";
  document.body.appendChild(tip);
  function hideTip() { tip.classList.remove("show"); }
  // measureEl: 見切れ判定に使う要素 / posEl: 位置・体裁を合わせる要素
  function showTip(measureEl, posEl, text) {
    if (!measureEl || !posEl) { hideTip(); return; }
    if (measureEl.scrollWidth <= measureEl.clientWidth + 1) { hideTip(); return; }  // 見切れていなければ出さない
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
  }
  toc.addEventListener("mouseover", (e) => {
    const row = e.target.closest(".tree-row");
    if (row) {
      const nm = row.querySelector(".tree-name");
      if (!nm) { hideTip(); return; }
      // .tree-name が flex item として幅を持てば nm で判定、持てない(幅0=インライン)なら行で判定
      const measure = (nm.clientWidth > 0) ? nm : row;
      showTip(measure, nm, nm.textContent);
      return;
    }
    const link = e.target.closest("#paneOutline a");
    if (link) { showTip(link, link, link.textContent); return; }
    hideTip();
  });
  toc.addEventListener("mouseleave", hideTip);
  toc.addEventListener("scroll", hideTip, true);  // スクロールで位置がずれるため隠す
  document.addEventListener("mousedown", hideTip);

  // ---- Open / close ----
  function setOpen(open) {
    toc.classList.toggle("open", open);
    document.body.classList.toggle("toc-open", open);
    localStorage.setItem("md-preview-toc-open", open ? "1" : "0");
    if (window._rebuildMinimap) window._rebuildMinimap();
  }
  tocBtn.addEventListener("click", () => setOpen(!toc.classList.contains("open")));
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key === "\\") {
      e.preventDefault();
      setOpen(!toc.classList.contains("open"));
    }
  });
  // ハンバーガー近接表示: 開いている時、サイドバー右端から一定範囲内（+56px）に
  // カーソルがあればボタンを出す。サイドバー外のボタンへマウスを移動しても消えない。
  document.addEventListener("mousemove", (e) => {
    if (!document.body.classList.contains("toc-open")) return;
    const rightEdge = toc.getBoundingClientRect().right;
    toc.classList.toggle("toggle-near", e.clientX <= rightEdge + 56);
  }, { passive: true });

  // ---- Seamless file load (右ペインのみ差し替え。ツリー状態は維持) ----
  function setActiveFile(abs) {
    paneFiles.querySelectorAll(".tree-file.active").forEach(a => a.classList.remove("active"));
    paneFiles.querySelectorAll(".tree-file").forEach(a => {
      if (a.dataset.abs === abs) a.classList.add("active");
    });
    updateFolderActive();
  }
  // 開いているファイルの祖先フォルダに has-active を付与（折り畳み時にCSSでハイライト）
  function updateFolderActive() {
    paneFiles.querySelectorAll(".tree-folder.has-active").forEach(li => li.classList.remove("has-active"));
    const act = paneFiles.querySelector(".tree-file.active");
    if (!act) return;
    let el = act.parentElement;
    while (el && el !== paneFiles) {
      if (el.classList && el.classList.contains("tree-folder")) el.classList.add("has-active");
      el = el.parentElement;
    }
  }
  function loadFile(abs, opts) {
    opts = opts || {};
    if (window.__editGuard && !window.__editGuard()) return;
    const keepScroll = !!opts.keepScroll;
    const prevY = window.scrollY;
    fetch("/render?path=" + encodeURIComponent(abs))
      .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(data => {
        mdContent.innerHTML = data.html;
        if (filePathEl) filePathEl.textContent = abs;
        if (data.title) document.title = data.title;
        window.__md.path = abs;
        window.__md.hash = data.hash;
        // rebuildOutlineを先に: __processContent内のensureBottomScrollRoomが最新の見出しで
        // 余白を計算できるようにする（__processContentは見出しを変更しないので順序入替は安全）。
        rebuildOutline();
        if (window.__processContent) window.__processContent();
        updateActive();
        setActiveFile(abs);
        if (opts.push !== false) {
          history.pushState({ path: abs }, "", "/view?path=" + encodeURIComponent(abs));
        }
        window.scrollTo(0, keepScroll ? prevY : 0);
      })
      .catch(() => { window.location = "/view?path=" + encodeURIComponent(abs); });
  }
  window.__reloadCurrent = function() { loadFile(window.__md.path, { push: false, keepScroll: true }); };
  window.addEventListener("popstate", (e) => {
    const p = e.state && e.state.path;
    if (p) loadFile(p, { push: false });
  });

  // ---- Files tree ----
  // インデントとガイド線はネストした子ulのCSS（.tree-children）で表現する。
  const FILE_SCROLL_THRESHOLD = 15; // 直下ファイルがこれを超えたらスクロール枠にまとめる
  // ファイル/フォルダ識別アイコン（Octiconsベースの線画、currentColor追従）
  function treeIcon(kind) {
    const span = document.createElement("span");
    span.className = "tree-icon";
    if (kind === "folder") {
      // 開いた/閉じたフォルダの両SVGを入れ、.collapsedクラスでCSSが出し分ける
      span.innerHTML =
        '<svg class="icon-open" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M.513 1.513A1.75 1.75 0 0 1 1.75 1h3.5c.55 0 1.07.26 1.4.7l.9 1.2a.25.25 0 0 0 .2.1H13a1 1 0 0 1 1 1v.5H2.75a.75.75 0 0 0 0 1.5h11.978a1 1 0 0 1 .994 1.117L15 13.25A1.75 1.75 0 0 1 13.25 15H1.75A1.75 1.75 0 0 1 0 13.25V2.75c0-.464.184-.91.513-1.237Z"/></svg>'
        + '<svg class="icon-closed" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75Z"/></svg>';
    } else {
      span.innerHTML = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Zm6.75.062V4.25c0 .138.112.25.25.25h2.688a.252.252 0 0 0-.011-.013l-2.914-2.914a.272.272 0 0 0-.013-.011Z"/></svg>';
    }
    return span;
  }
  function buildTree(files) {
    const root = { dirs: {}, files: [] };
    files.forEach(f => {
      const parts = f.rel.split("/");
      let node = root;
      for (let i = 0; i < parts.length - 1; i++) {
        const d = parts[i];
        node.dirs[d] = node.dirs[d] || { dirs: {}, files: [] };
        node = node.dirs[d];
      }
      node.files.push({ name: parts[parts.length - 1], abs: f.abs });
    });
    return root;
  }
  // 現在ファイルへ至るフォルダパスを展開状態にするための集合
  function pathDirs(rel) {
    const parts = rel.split("/");
    const set = {};
    let acc = "";
    for (let i = 0; i < parts.length - 1; i++) {
      acc = acc ? acc + "/" + parts[i] : parts[i];
      set[acc] = true;
    }
    return set;
  }
  function renderInto(ul, node, prefix, depth, openDirs) {
    Object.keys(node.dirs).sort().forEach(name => {
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
    });
    const sortedFiles = node.files.sort((a, b) => a.name.localeCompare(b.name));
    // 直下ファイルが多い場合は固定高スクロール枠にまとめる
    let fileContainer = ul;
    if (sortedFiles.length > FILE_SCROLL_THRESHOLD) {
      const boxLi = document.createElement("li");
      const box = document.createElement("div");
      box.className = "tree-filebox";
      const innerUl = document.createElement("ul");
      innerUl.className = "toc-tree";
      box.appendChild(innerUl);
      boxLi.appendChild(box);
      ul.appendChild(boxLi);
      fileContainer = innerUl;
    }
    sortedFiles.forEach(f => {
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
      a.addEventListener("click", (e) => { e.preventDefault(); loadFile(f.abs, { push: true }); });
      li.appendChild(a);
      fileContainer.appendChild(li);
    });
  }

  function finalize() {
    const hasOutline = links.length > 0;
    const hasFiles = paneFiles.childElementCount > 0;
    applyTocMode();
    tocBtn.style.display = (hasOutline || hasFiles) ? "" : "none";
    const savedOpen = localStorage.getItem("md-preview-toc-open") === "1";
    setOpen(savedOpen && (hasOutline || hasFiles));
  }

  // 初期化: アウトライン構築 → 一度確定 → ファイル一覧（git）を一度だけ取得して確定
  // 初回の top-level __processContent はリンク構築前に走るため、ここで余白を算定し直す。
  rebuildOutline();
  ensureBottomScrollRoom();
  if (window._rebuildMinimap) window._rebuildMinimap();  // 余白反映後にミニマップを再構築
  updateActive();
  finalize();
  history.replaceState({ path: window.__md.path }, "", location.href);
  fetch("/files?path=" + encodeURIComponent(window.__md.path))
    .then(r => r.json())
    .then(data => {
      const files = (data && data.files) || [];
      if (files.length > 1) {
        const tree = buildTree(files);
        const cur = files.find(f => f.abs === window.__md.path);
        const openDirs = cur ? pathDirs(cur.rel) : {};
        const rootUl = document.createElement("ul");
        rootUl.className = "toc-tree";
        renderInto(rootUl, tree, "", 0, openDirs);
        paneFiles.appendChild(rootUl);
        updateFolderActive();
        const act = paneFiles.querySelector(".tree-file.active");
        if (act) act.scrollIntoView({ block: "center" });
      }
      finalize();
    })
    .catch(() => {});
})();

// --- Minimap ---
(function() {
  const minimap = document.getElementById("minimap");
  const minimapContent = document.getElementById("minimapContent");
  const minimapViewport = document.getElementById("minimapViewport");
  var scaleX, contentOriginalHeight;

  function buildMinimapContent() {
    minimapContent.innerHTML = "";
    const contentSource = document.querySelector(".file-path");
    let el = contentSource;
    while (el) {
      if (el !== minimap && el.id !== "settingsBtn" && el.id !== "settingsModal" && el.id !== "settingsOverlay"
          && el.id !== "toc" && el.id !== "tocToggle") {
        minimapContent.appendChild(el.cloneNode(true));
      }
      el = el.nextElementSibling;
    }
  }

  function applyScale() {
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
    if (scaledContentH < minimapH) {
      minimap.style.height = scaledContentH + "px";
    }
  }

  // 未処理の mermaid 図がある間は初期構築を遅延し、mermaid.run().finally() 内の
  // _rebuildMinimap() に任せる（描画途中の clone 競合を避ける）。
  if (!(window.mermaid && document.querySelector(".mermaid:not([data-processed])"))) {
    buildMinimapContent();
    applyScale();
  }

  window._rebuildMinimap = function() { buildMinimapContent(); applyScale(); updateViewport(); };
  window._updateMinimapScale = function() { applyScale(); updateViewport(); };

  function updateViewport() {
    const docHeight = document.documentElement.scrollHeight;
    const viewHeight = window.innerHeight;
    const scrollTop = window.scrollY;
    const maxDocScroll = docHeight - viewHeight;
    const minimapH = minimap.clientHeight;
    const scaledContentH = contentOriginalHeight * scaleX;

    // Viewport indicator size in scaled pixels
    const vpHeight = Math.max(10, (viewHeight / docHeight) * scaledContentH);

    if (scaledContentH <= minimapH) {
      // Entire document fits in minimap — no minimap scrolling
      minimapContent.style.top = "0px";
      const vpTop = maxDocScroll > 0 ? (scrollTop / maxDocScroll) * (scaledContentH - vpHeight) : 0;
      minimapViewport.style.top = Math.max(0, vpTop) + "px";
      minimapViewport.style.height = vpHeight + "px";
    } else {
      // Document overflows minimap — scroll minimap proportionally
      const scrollFraction = maxDocScroll > 0 ? scrollTop / maxDocScroll : 0;
      const maxContentOffset = scaledContentH - minimapH;
      const contentOffset = scrollFraction * maxContentOffset;
      // top is in pre-transform coords, so divide by scale
      minimapContent.style.top = -(contentOffset / scaleX) + "px";

      const vpTop = scrollFraction * (minimapH - vpHeight);
      minimapViewport.style.top = Math.max(0, vpTop) + "px";
      minimapViewport.style.height = vpHeight + "px";
    }
  }

  window.addEventListener("scroll", updateViewport);
  window.addEventListener("resize", function() { applyScale(); updateViewport(); });
  updateViewport();

  // Click/drag to scroll — clicked position becomes viewport center
  function scrollToMinimapPos(clientY) {
    const rect = minimap.getBoundingClientRect();
    const y = clientY - rect.top;
    const minimapH = minimap.clientHeight;
    const scaledContentH = contentOriginalHeight * scaleX;
    const docHeight = document.documentElement.scrollHeight;
    const viewHeight = window.innerHeight;
    const maxDocScroll = docHeight - viewHeight;

    // Map click position to document fraction
    var docFraction;
    if (scaledContentH <= minimapH) {
      docFraction = scaledContentH > 0 ? y / scaledContentH : 0;
    } else {
      docFraction = y / minimapH;
    }
    // Scroll so the clicked position is at the center of the viewport
    const targetScroll = docFraction * docHeight - viewHeight / 2;
    window.scrollTo({ top: Math.max(0, Math.min(targetScroll, maxDocScroll)), behavior: "instant" });
  }

  minimap.addEventListener("mousedown", function(e) {
    e.preventDefault();
    scrollToMinimapPos(e.clientY);
    function onDrag(ev) {
      scrollToMinimapPos(ev.clientY);
    }
    function onUp() {
      document.removeEventListener("mousemove", onDrag);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onDrag);
    document.addEventListener("mouseup", onUp);
  });
})();
