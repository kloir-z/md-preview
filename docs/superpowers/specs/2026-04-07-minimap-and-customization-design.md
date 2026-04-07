# ミニマップ + カスタマイズパネル 設計

## 概要

Markdownプレビューサーバーに以下の機能を追加する:
1. VSCodeスタイルのミニマップ（画面右端）
2. カスタマイズモーダル（テーマ選択・カラーインポート・レイアウト設定）

## 1. ミニマップ（CSS Transform方式）

### 仕様
- 画面右端に `position: fixed` で固定表示
- コンテンツのクローンを `transform: scale()` で縮小表示（スケール比率: コンテンツ高さとビューポート高さの比率で動的算出）
- 現在のビューポート位置を半透明ハイライト（viewport indicator）で表示
- クリックでその位置にスクロール、ドラッグでスクロール追従
- テーマ切替に自動追従（同じCSS変数を使用するため）
- ミニマップ幅: 約80px、bodyのmax-widthとは独立配置

### DOM構造
```html
<div class="minimap" id="minimap">
  <div class="minimap-content" id="minimapContent">
    <!-- bodyコンテンツのcloneNode(true) -->
  </div>
  <div class="minimap-viewport" id="minimapViewport"></div>
</div>
```

### 動作
- ページロード時にbodyのコンテンツ要素をクローンしてミニマップに挿入
- `scroll`イベントでviewport indicatorの位置を更新
- ミニマップ上のクリック/ドラッグで `window.scrollTo()` を呼び出し
- クローン内のリンクやボタンはクリック無効化（`pointer-events: none`、viewport indicatorのみ操作可能）

## 2. カスタマイズパネル（モーダル）

### UI構成
既存の歯車ボタン（右下固定）クリックで中央モーダルを表示。背景はオーバーレイで暗くする。

#### セクション:

**Theme（テーマ選択）**
- 既存の8テーマをリスト表示
- 選択中のテーマにチェックマーク
- 「Custom」テーマ（カラーインポート時に自動追加）

**Import Colors（カラーインポート）**
- テキストエリア: .itermcolorsのXML plistを貼り付け
- 参考リンク: [iTerm2 Color Schemes](https://iterm2colorschemes.com/)
- 「Apply」ボタンでパース＆適用
- パースエラー時はテキストエリア下にエラーメッセージ表示

**Layout（レイアウト設定）**
- 箇条書き後マージン: スライダー（0px〜2em、デフォルト: ブラウザデフォルト）
- 最大横幅: スライダー（600px〜1200px、デフォルト: 800px）

### モーダルCSS
- 中央配置、max-width: 480px
- 背景: `var(--code-bg)`、ボーダー: `var(--border)`
- オーバーレイ: 半透明黒
- 閉じる: 右上の×ボタン、またはオーバーレイクリック

## 3. カラーインポート処理

### パース
- `DOMParser`でXMLをパース
- `<key>`タグからカラー名を取得、対応する`<dict>`からR/G/B（0.0〜1.0 float）を読み取り
- `(Dark)` / `(Light)` サフィックスのないベースキーを使用

### 色変換
- R/G/B float値 → `Math.round(val * 255)` → `#rrggbb` hex

### マッピング
| .itermcolors キー | CSS変数 | 用途 |
|---|---|---|
| Background Color | `--bg` | 背景色 |
| Foreground Color | `--fg` | テキスト色 |
| Ansi 0 Color | `--code-bg` | コードブロック背景 |
| Ansi 8 Color | `--border`, `--blockquote-border` | ボーダー類 |
| Ansi 4 Color | `--link` | リンク色 |
| Ansi 3 Color | `--heading` | 見出し色 |
| Ansi 5 Color | `--accent` | インラインコード色 |
| Ansi 8 Color | `--file-path`, `--blockquote-fg` | 控えめテキスト |
| Background Colorを少し明るく(+10) | `--table-stripe` | テーブル縞模様 |

## 4. 永続化（localStorage）

| キー | 値 | デフォルト |
|---|---|---|
| `md-preview-theme` | テーマキー文字列 | `"monokai"` |
| `md-preview-custom-theme` | カスタムテーマのCSS変数JSON | なし |
| `md-preview-list-margin` | 箇条書きマージン値（CSS値） | ブラウザデフォルト |
| `md-preview-max-width` | 最大横幅値（px） | `800` |

ページロード時にlocalStorageから読み込み、即座に適用する（既存のテーマ適用と同じ `<script>` in `<head>` 方式）。

## 5. 実装範囲

- **変更ファイル**: `md_server.py` の `HTML_TEMPLATE` 内（HTML/CSS/JS）のみ
- サーバー側のPythonロジック変更なし
- 新規ファイルなし
- 既存のテーマ切替ロジック・設定パネルUIを置き換え（ポップアップ → モーダル）
