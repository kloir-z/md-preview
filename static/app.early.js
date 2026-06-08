// UI重ね色（ホバー/ハイライト/スクロールバー等）。ダーク=白系/ライト=黒系。
// 全テーマがこの6キーを必ず持つことで、テーマ切替時に前テーマの残留を防ぐ。
const _OVL_DARK = {
  "--overlay-faint": "rgba(255,255,255,0.02)", "--overlay-active": "rgba(255,255,255,0.04)",
  "--overlay-hover": "rgba(255,255,255,0.06)", "--overlay-soft": "rgba(255,255,255,0.16)",
  "--overlay-medium": "rgba(255,255,255,0.20)", "--overlay-strong": "rgba(255,255,255,0.30)",
};
const _OVL_LIGHT = {
  "--overlay-faint": "rgba(0,0,0,0.02)", "--overlay-active": "rgba(0,0,0,0.05)",
  "--overlay-hover": "rgba(0,0,0,0.06)", "--overlay-soft": "rgba(0,0,0,0.18)",
  "--overlay-medium": "rgba(0,0,0,0.22)", "--overlay-strong": "rgba(0,0,0,0.30)",
};
// 各テーマ: name=表示名, dark=明暗(mermaid連動), code=対応hljsキー(コードテーマ連動)。
const THEMES = {
  monokai: {
    name: "Monokai", dark: true, code: "monokai", ..._OVL_DARK,
    "--bg": "#272822", "--fg": "#d8d8d2", "--border": "#3e3f3a",
    "--code-bg": "#1e1f1c", "--blockquote-fg": "#8f908a",
    "--blockquote-border": "#3e3f3a", "--link": "#66c2b5",
    "--file-path": "#8f908a", "--table-stripe": "#2e2f2a",
    "--heading": "#d4a76a", "--accent": "#ae9fcc",
  },
  github_dark: {
    name: "GitHub Dark", dark: true, code: "github-dark", ..._OVL_DARK,
    "--bg": "#0d1117", "--fg": "#e6edf3", "--border": "#30363d",
    "--code-bg": "#161b22", "--blockquote-fg": "#8b949e",
    "--blockquote-border": "#30363d", "--link": "#58a6ff",
    "--file-path": "#8b949e", "--table-stripe": "#161b22",
    "--heading": "#e6edf3", "--accent": "#bc8cff",
  },
  dracula: {
    name: "Dracula", dark: true, code: "dracula", ..._OVL_DARK,
    "--bg": "#282a36", "--fg": "#f8f8f2", "--border": "#44475a",
    "--code-bg": "#21222c", "--blockquote-fg": "#6272a4",
    "--blockquote-border": "#44475a", "--link": "#8be9fd",
    "--file-path": "#6272a4", "--table-stripe": "#2d2f3d",
    "--heading": "#bd93f9", "--accent": "#ff79c6",
  },
  nord: {
    name: "Nord", dark: true, code: "nord", ..._OVL_DARK,
    "--bg": "#2e3440", "--fg": "#d8dee9", "--border": "#3b4252",
    "--code-bg": "#272c36", "--blockquote-fg": "#7b88a1",
    "--blockquote-border": "#3b4252", "--link": "#88c0d0",
    "--file-path": "#7b88a1", "--table-stripe": "#333a47",
    "--heading": "#81a1c1", "--accent": "#b48ead",
  },
  solarized_dark: {
    name: "Solarized Dark", dark: true, code: "github-dark", ..._OVL_DARK,
    "--bg": "#002b36", "--fg": "#839496", "--border": "#073642",
    "--code-bg": "#01313f", "--blockquote-fg": "#657b83",
    "--blockquote-border": "#073642", "--link": "#268bd2",
    "--file-path": "#657b83", "--table-stripe": "#073642",
    "--heading": "#b58900", "--accent": "#2aa198",
  },
  gruvbox_dark: {
    name: "Gruvbox Dark", dark: true, code: "github-dark", ..._OVL_DARK,
    "--bg": "#282828", "--fg": "#ebdbb2", "--border": "#3c3836",
    "--code-bg": "#1d2021", "--blockquote-fg": "#a89984",
    "--blockquote-border": "#3c3836", "--link": "#83a598",
    "--file-path": "#a89984", "--table-stripe": "#302e2b",
    "--heading": "#fabd2f", "--accent": "#d3869b",
  },
  catppuccin_mocha: {
    name: "Catppuccin Mocha", dark: true, code: "atom-one-dark", ..._OVL_DARK,
    "--bg": "#1e1e2e", "--fg": "#cdd6f4", "--border": "#313244",
    "--code-bg": "#181825", "--blockquote-fg": "#a6adc8",
    "--blockquote-border": "#313244", "--link": "#89b4fa",
    "--file-path": "#a6adc8", "--table-stripe": "#232336",
    "--heading": "#cba6f7", "--accent": "#f5c2e7",
  },
  tokyo_night: {
    name: "Tokyo Night", dark: true, code: "tokyo-night-dark", ..._OVL_DARK,
    "--bg": "#1a1b26", "--fg": "#a9b1d6", "--border": "#292e42",
    "--code-bg": "#16161e", "--blockquote-fg": "#565f89",
    "--blockquote-border": "#292e42", "--link": "#7aa2f7",
    "--file-path": "#565f89", "--table-stripe": "#1f2030",
    "--heading": "#bb9af7", "--accent": "#f7768e",
  },
  one_dark: {
    name: "One Dark", dark: true, code: "atom-one-dark", ..._OVL_DARK,
    "--bg": "#282c34", "--fg": "#abb2bf", "--border": "#3b4048",
    "--code-bg": "#21252b", "--blockquote-fg": "#7f848e",
    "--blockquote-border": "#3b4048", "--link": "#61afef",
    "--file-path": "#7f848e", "--table-stripe": "#2c313a",
    "--heading": "#e5c07b", "--accent": "#c678dd",
  },
  night_owl: {
    name: "Night Owl", dark: true, code: "tokyo-night-dark", ..._OVL_DARK,
    "--bg": "#011627", "--fg": "#d6deeb", "--border": "#1d3b53",
    "--code-bg": "#01111d", "--blockquote-fg": "#637777",
    "--blockquote-border": "#1d3b53", "--link": "#82aaff",
    "--file-path": "#637777", "--table-stripe": "#0b2942",
    "--heading": "#ecc48d", "--accent": "#c792ea",
  },
  rose_pine: {
    name: "Rosé Pine", dark: true, code: "dracula", ..._OVL_DARK,
    "--bg": "#191724", "--fg": "#e0def4", "--border": "#26233a",
    "--code-bg": "#1f1d2e", "--blockquote-fg": "#908caa",
    "--blockquote-border": "#26233a", "--link": "#9ccfd8",
    "--file-path": "#908caa", "--table-stripe": "#21202e",
    "--heading": "#ebbcba", "--accent": "#c4a7e7",
  },
  github_light: {
    name: "GitHub Light", dark: false, code: "github", ..._OVL_LIGHT,
    "--bg": "#ffffff", "--fg": "#1f2328", "--border": "#d1d9e0",
    "--code-bg": "#f6f8fa", "--blockquote-fg": "#59636e",
    "--blockquote-border": "#d1d9e0", "--link": "#0969da",
    "--file-path": "#59636e", "--table-stripe": "#f6f8fa",
    "--heading": "#1f2328", "--accent": "#8250df",
  },
  solarized_light: {
    name: "Solarized Light", dark: false, code: "solarized-light", ..._OVL_LIGHT,
    "--bg": "#fdf6e3", "--fg": "#657b83", "--border": "#eee8d5",
    "--code-bg": "#eee8d5", "--blockquote-fg": "#93a1a1",
    "--blockquote-border": "#d3cbb7", "--link": "#268bd2",
    "--file-path": "#93a1a1", "--table-stripe": "#f5efdc",
    "--heading": "#b58900", "--accent": "#2aa198",
  },
  catppuccin_latte: {
    name: "Catppuccin Latte", dark: false, code: "atom-one-light", ..._OVL_LIGHT,
    "--bg": "#eff1f5", "--fg": "#4c4f69", "--border": "#ccd0da",
    "--code-bg": "#e6e9ef", "--blockquote-fg": "#6c6f85",
    "--blockquote-border": "#ccd0da", "--link": "#1e66f5",
    "--file-path": "#6c6f85", "--table-stripe": "#e6e9ef",
    "--heading": "#7287fd", "--accent": "#8839ef",
  },
  gruvbox_light_soft: {
    name: "Gruvbox Light Soft", dark: false, code: "github", ..._OVL_LIGHT,
    "--bg": "#f2e5bc", "--fg": "#504945", "--border": "#ddd0a8",
    "--code-bg": "#ece0b8", "--blockquote-fg": "#7c6f64",
    "--blockquote-border": "#ddd0a8", "--link": "#076678",
    "--file-path": "#7c6f64", "--table-stripe": "#ece0b8",
    "--heading": "#b57614", "--accent": "#8f3f71",
  },
  everforest_soft: {
    name: "Everforest Soft", dark: true, code: "nord", ..._OVL_DARK,
    "--bg": "#2d353b", "--fg": "#d3c6aa", "--border": "#4f5b58",
    "--code-bg": "#272e33", "--blockquote-fg": "#9da9a0",
    "--blockquote-border": "#4f5b58", "--link": "#7fbbb3",
    "--file-path": "#9da9a0", "--table-stripe": "#343f44",
    "--heading": "#dbbc7f", "--accent": "#d699b6",
  },
};

// コードブロックのシンタックスハイライト用テーマ（highlight.js）。
// /static/hljs/<key>.min.css を id="hljsTheme" のlinkに差し替えて切替える。
// アプリ（ページ）テーマとは独立。背景は --code-bg に統一しトークン色のみ反映。
const CODE_THEMES = [
  { key: "github-dark", name: "GitHub Dark" },
  { key: "atom-one-dark", name: "Atom One Dark" },
  { key: "tokyo-night-dark", name: "Tokyo Night Dark" },
  { key: "monokai", name: "Monokai" },
  { key: "dracula", name: "Dracula" },
  { key: "nord", name: "Nord" },
  { key: "vs2015", name: "VS 2015" },
  { key: "a11y-dark", name: "a11y Dark" },
  { key: "github", name: "GitHub Light" },
  { key: "atom-one-light", name: "Atom One Light" },
  { key: "solarized-light", name: "Solarized Light" },
];
const DEFAULT_CODE_THEME = "github-dark";
function applyCodeTheme(key) {
  const link = document.getElementById("hljsTheme");
  if (link) link.href = "/static/hljs/" + key + ".min.css";
}

function applyTheme(keyOrTheme) {
  const theme = (typeof keyOrTheme === "string") ? THEMES[keyOrTheme] : keyOrTheme;
  if (!theme) return;
  const root = document.documentElement;
  Object.keys(theme).forEach(k => {
    if (k.startsWith("--")) root.style.setProperty(k, theme[k]);
  });
  // テーマ本来のfg/accent（ユーザー色を解除した時に戻す基準。dim/上書きの累積を防ぐ）
  if (theme["--fg"]) root.style.setProperty("--fg-theme", theme["--fg"]);
  if (theme["--accent"]) root.style.setProperty("--accent-theme", theme["--accent"]);
}

// ユーザーのカスタム色はテーマの明暗(dark/light)別に保存する（真逆の明暗への持ち越しで
// 見えなくなるのを防ぐ）。現在テーマの dark フラグから "dark" / "light" を返す。
function _userColorMode() {
  const t = THEMES[localStorage.getItem("md-preview-theme") || "monokai"];
  return (t && t.dark === false) ? "light" : "dark";
}

let savedTheme = localStorage.getItem("md-preview-theme") || "monokai";
if (!THEMES[savedTheme]) {
  // 旧カラーインポートの "custom" 等、未知のテーマキーは既定へ正規化する。
  savedTheme = "monokai";
  localStorage.setItem("md-preview-theme", savedTheme);
  localStorage.removeItem("md-preview-custom-theme");
  localStorage.removeItem("md-preview-palette");
}
applyTheme(savedTheme);
const savedCodeTheme = localStorage.getItem("md-preview-code-theme") || DEFAULT_CODE_THEME;
applyCodeTheme(savedCodeTheme);
// ユーザーが上書きした色。テーマ切替で上書きされるため、テーマ適用のたびに再適用する。
function _parseColor(s) {
  s = (s || "").trim();
  if (s[0] === "#") {
    if (s.length === 4) s = "#" + s[1]+s[1]+s[2]+s[2]+s[3]+s[3];
    if (s.length >= 7) return [parseInt(s.slice(1,3),16), parseInt(s.slice(3,5),16), parseInt(s.slice(5,7),16)];
  }
  const m = s.match(/rgba?\(([^)]+)\)/);
  if (m) { const p = m[1].split(",").map(x => parseFloat(x)); return [p[0]||0, p[1]||0, p[2]||0]; }
  return null;
}
// RGBをf倍して暗くする（まぶしさ低減の明度調整。f=1で無変化）
function _dim(color, f) {
  const rgb = _parseColor(color);
  if (!rgb) return color;
  const d = c => Math.max(0, Math.min(255, Math.round(c * f)));
  return "rgb(" + d(rgb[0]) + "," + d(rgb[1]) + "," + d(rgb[2]) + ")";
}
// 旧（明暗共通）キーを dark 用へ一度だけ移行する。既存ユーザーのダーク向け設定を保持し、
// 以降は明暗別キー(md-preview-<key>-dark / -light)で扱う。
(function _migrateUserColors() {
  ["--fg","--h1-color","--h2-color","--h3-color","--h4-color"].forEach(k => {
    const old = localStorage.getItem("md-preview-" + k);
    if (old != null) {
      if (localStorage.getItem("md-preview-" + k + "-dark") == null)
        localStorage.setItem("md-preview-" + k + "-dark", old);
      localStorage.removeItem("md-preview-" + k);
    }
  });
  const ob = localStorage.getItem("md-preview-fg-brightness");
  if (ob != null) {
    if (localStorage.getItem("md-preview-fg-brightness-dark") == null)
      localStorage.setItem("md-preview-fg-brightness-dark", ob);
    localStorage.removeItem("md-preview-fg-brightness");
  }
})();
// 本文色: 選択色（無ければテーマの--fg）を明度(brightness%)で暗くして適用。明暗別に保存。
function applyBodyColor() {
  const mode = _userColorMode();
  const base = localStorage.getItem("md-preview--fg-" + mode);
  const b = parseInt(localStorage.getItem("md-preview-fg-brightness-" + mode) || "100", 10);
  const root = document.documentElement;
  const themeFg = getComputedStyle(root).getPropertyValue("--fg-theme").trim();
  if (!base && b >= 100) {
    // 既定に戻す: テーマの素のfgを再適用（過去のdim結果を残さない）
    if (themeFg) root.style.setProperty("--fg", themeFg);
    return;
  }
  // 基準色は「選択色」または「テーマの素のfg」。現在の--fg（dim済みかも）は使わない＝累積防止。
  const baseColor = base || themeFg || getComputedStyle(root).getPropertyValue("--fg").trim();
  root.style.setProperty("--fg", _dim(baseColor, b / 100));
}
function applyUserColors() {
  const mode = _userColorMode();
  const root = document.documentElement;
  ["--h1-color","--h2-color","--h3-color","--h4-color"].forEach(k => {
    const v = localStorage.getItem("md-preview-" + k + "-" + mode);
    if (v) root.style.setProperty(k, v);
    else root.style.removeProperty(k);  // 未設定→テーマ既定(:rootのvar(--heading))へ戻す
  });
  // インラインコード色(--accent)。未設定ならテーマ既定(--accent-theme)へ戻す。
  const ac = localStorage.getItem("md-preview--accent-" + mode);
  if (ac) {
    root.style.setProperty("--accent", ac);
  } else {
    const acTheme = getComputedStyle(root).getPropertyValue("--accent-theme").trim();
    if (acTheme) root.style.setProperty("--accent", acTheme);
  }
  applyBodyColor();
}
applyUserColors();
const savedListMargin = localStorage.getItem("md-preview-list-margin");
if (savedListMargin) document.documentElement.style.setProperty("--list-margin", savedListMargin + "px");
const savedMaxWidth = localStorage.getItem("md-preview-max-width");
