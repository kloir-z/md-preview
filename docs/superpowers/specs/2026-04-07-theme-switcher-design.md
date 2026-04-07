# テーマ切替機能 設計

## 概要

Markdownプレビューのデザイン・配色を複数のダーク系テーマから切り替えられるようにする。設定はlocalStorageに保存し、歯車アイコンから設定パネルを開いて切り替える。

## 要件

- ダーク系8テーマをプリセットとして用意
- 画面右下の歯車アイコンをクリックで設定パネルを開閉
- テーマ選択は即座に反映（リロード不要）
- 選択したテーマはlocalStorageに永続化
- コードハイライトはMonokai固定（highlight.js テーマは切り替えない）

## アプローチ

クライアントサイド完結（アプローチB）。テーマ定義をJS内に持ち、CSS変数の上書きで切り替える。サーバー側の変更は最小限。

## テーマ一覧

| テーマ | ベース色 | 特徴 |
|--------|----------|------|
| Monokai (デフォルト) | `#272822` | 現行テーマ。暖色系アクセント |
| GitHub Dark | `#0d1117` | 青系リンク、モダン |
| Dracula | `#282a36` | ピンク・紫系アクセント |
| Nord | `#2e3440` | 寒色系、北欧風 |
| Solarized Dark | `#002b36` | ティール系、目に優しい |
| Gruvbox Dark | `#282828` | 暖色レトロ、オレンジ・黄色 |
| Catppuccin Mocha | `#1e1e2e` | パステル系、柔らかい |
| Tokyo Night | `#1a1b26` | 藍系、落ち着いたネオン風 |

## テーマデータ構造

JSオブジェクトとして定義。各テーマは現行のCSS変数（11個）に対応する値を持つ。

```js
const THEMES = {
  monokai: {
    name: "Monokai",
    "--bg": "#272822",
    "--fg": "#d8d8d2",
    "--border": "#3e3f3a",
    "--code-bg": "#1e1f1c",
    "--blockquote-fg": "#8f908a",
    "--blockquote-border": "#3e3f3a",
    "--link": "#66c2b5",
    "--file-path": "#8f908a",
    "--table-stripe": "#2e2f2a",
    "--heading": "#d4a76a",
    "--accent": "#ae9fcc",
  },
  // 他テーマも同構造
};
```

## 設定パネルUI

- 画面右下に `position: fixed` の歯車アイコン（⚙）
- クリックでテーマ名リストのパネルを表示
- 現在選択中のテーマにチェックマーク表示
- パネル外クリックで閉じる
- パネル自体のスタイルはテーマに連動（CSS変数を使用）

## 永続化

- キー: `md-preview-theme`
- 値: テーマキー文字列（例: `"monokai"`, `"dracula"`）
- デフォルト: `monokai`

## FOUC防止

`<style>` 定義直後、`<body>` 直前に `<script>` ブロックを配置。localStorageからテーマを読み取り、CSS変数を即座に適用する。

```html
<style>
  :root { /* monokaiのデフォルト値 */ }
</style>
<script>
  // THEMES定義 + localStorage読み取り + CSS変数適用
</script>
</head>
<body>
```

## サーバー側の変更

- `md_server.py` の `HTML_TEMPLATE` にテーマJS・設定パネルHTML/CSSを追加
- `:root` のCSS変数はmonokaiの値をデフォルトとして残す（JS無効時のフォールバック）
- サーバーのPythonロジックに変更なし

## スコープ外

- ライトテーマ
- highlight.jsテーマの連動切替
- フォントサイズ・行間等のレイアウト調整
- テーマのユーザー定義・カスタムカラー
