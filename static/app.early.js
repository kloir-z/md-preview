const THEMES = {
  monokai: {
    name: "Monokai",
    "--bg": "#272822", "--fg": "#d8d8d2", "--border": "#3e3f3a",
    "--code-bg": "#1e1f1c", "--blockquote-fg": "#8f908a",
    "--blockquote-border": "#3e3f3a", "--link": "#66c2b5",
    "--file-path": "#8f908a", "--table-stripe": "#2e2f2a",
    "--heading": "#d4a76a", "--accent": "#ae9fcc",
  },
  github_dark: {
    name: "GitHub Dark",
    "--bg": "#0d1117", "--fg": "#e6edf3", "--border": "#30363d",
    "--code-bg": "#161b22", "--blockquote-fg": "#8b949e",
    "--blockquote-border": "#30363d", "--link": "#58a6ff",
    "--file-path": "#8b949e", "--table-stripe": "#161b22",
    "--heading": "#e6edf3", "--accent": "#bc8cff",
  },
  dracula: {
    name: "Dracula",
    "--bg": "#282a36", "--fg": "#f8f8f2", "--border": "#44475a",
    "--code-bg": "#21222c", "--blockquote-fg": "#6272a4",
    "--blockquote-border": "#44475a", "--link": "#8be9fd",
    "--file-path": "#6272a4", "--table-stripe": "#2d2f3d",
    "--heading": "#bd93f9", "--accent": "#ff79c6",
  },
  nord: {
    name: "Nord",
    "--bg": "#2e3440", "--fg": "#d8dee9", "--border": "#3b4252",
    "--code-bg": "#272c36", "--blockquote-fg": "#7b88a1",
    "--blockquote-border": "#3b4252", "--link": "#88c0d0",
    "--file-path": "#7b88a1", "--table-stripe": "#333a47",
    "--heading": "#81a1c1", "--accent": "#b48ead",
  },
  solarized_dark: {
    name: "Solarized Dark",
    "--bg": "#002b36", "--fg": "#839496", "--border": "#073642",
    "--code-bg": "#01313f", "--blockquote-fg": "#657b83",
    "--blockquote-border": "#073642", "--link": "#268bd2",
    "--file-path": "#657b83", "--table-stripe": "#073642",
    "--heading": "#b58900", "--accent": "#2aa198",
  },
  gruvbox_dark: {
    name: "Gruvbox Dark",
    "--bg": "#282828", "--fg": "#ebdbb2", "--border": "#3c3836",
    "--code-bg": "#1d2021", "--blockquote-fg": "#a89984",
    "--blockquote-border": "#3c3836", "--link": "#83a598",
    "--file-path": "#a89984", "--table-stripe": "#302e2b",
    "--heading": "#fabd2f", "--accent": "#d3869b",
  },
  catppuccin_mocha: {
    name: "Catppuccin Mocha",
    "--bg": "#1e1e2e", "--fg": "#cdd6f4", "--border": "#313244",
    "--code-bg": "#181825", "--blockquote-fg": "#a6adc8",
    "--blockquote-border": "#313244", "--link": "#89b4fa",
    "--file-path": "#a6adc8", "--table-stripe": "#232336",
    "--heading": "#cba6f7", "--accent": "#f5c2e7",
  },
  tokyo_night: {
    name: "Tokyo Night",
    "--bg": "#1a1b26", "--fg": "#a9b1d6", "--border": "#292e42",
    "--code-bg": "#16161e", "--blockquote-fg": "#565f89",
    "--blockquote-border": "#292e42", "--link": "#7aa2f7",
    "--file-path": "#565f89", "--table-stripe": "#1f2030",
    "--heading": "#bb9af7", "--accent": "#f7768e",
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
  // テーマ本来のfg（明度調整の基準。dim結果が累積しないよう素の値を保持）
  if (theme["--fg"]) root.style.setProperty("--fg-theme", theme["--fg"]);
}

const savedTheme = localStorage.getItem("md-preview-theme") || "monokai";
if (savedTheme === "custom") {
  const ct = localStorage.getItem("md-preview-custom-theme");
  if (ct) applyTheme(JSON.parse(ct));
} else {
  applyTheme(savedTheme);
}
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
// 本文色: 選択色（無ければテーマの--fg）を明度(brightness%)で暗くして適用
function applyBodyColor() {
  const base = localStorage.getItem("md-preview--fg");
  const b = parseInt(localStorage.getItem("md-preview-fg-brightness") || "100", 10);
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
  ["--h1-color","--h2-color","--h3-color","--h4-color"].forEach(k => {
    const v = localStorage.getItem("md-preview-" + k);
    if (v) document.documentElement.style.setProperty(k, v);
  });
  applyBodyColor();
}
applyUserColors();
const savedListMargin = localStorage.getItem("md-preview-list-margin");
if (savedListMargin) document.documentElement.style.setProperty("--list-margin", savedListMargin + "px");
const savedMaxWidth = localStorage.getItem("md-preview-max-width");
