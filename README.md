# md-preview

ローカルのMarkdownファイルをブラウザでプレビューするPythonサーバー。  
複数テーマ対応 + highlight.jsコードハイライト。ファイル変更時に自動リロード。

## 機能

- **複数テーマ**: 8種のダーク系プリセットテーマをドロップダウンで切替
- **カラーインポート**: [iTerm2 Color Schemes](https://iterm2colorschemes.com/) の `.itermcolors` XMLを貼り付けてカスタムテーマを作成
- **見出し色カスタマイズ**: インポートしたパレットからH1〜H4の色を個別選択（シャッフルボタン付き）
- **レイアウト設定**: 箇条書き後マージン・最大横幅・ミニマップ幅をスライダーで調整
- **ミニマップ**: 画面右端にVSCodeスタイルのミニマップ表示（クリック/ドラッグでスクロール）。左端のハンドルをドラッグして幅変更
- **サイドバー**: 左に Outline（見出し目次・スクロール追従）と Files（同じgitリポジトリ内の`.md`フォルダツリー）タブ。Filesからファイルを選ぶと**ページ再読込なしで右ペインだけ切替**（高速・ツリーの開閉状態も維持）。右端のハンドルをドラッグして幅変更
- **自動リロード**: ファイル変更をMD5ポーリングで検知し、再読込なしで自動更新
- **設定永続化**: すべての設定（テーマ・色・レイアウト・各ペイン幅）をlocalStorageに保存

## 必要なもの

- Python 3.10+
- `markdown` パッケージ

## セットアップ

```bash
git clone https://github.com/kloir-z/md-preview.git
cd md-preview
pip install -r requirements.txt
```

> **Note:** 依存が `markdown` 1パッケージのみのため、venvは使わずグローバルインストールで運用している。

## 使い方

### オープナーで開く

```bash
pythonw md_open.pyw path/to/file.md
```

`md_open.pyw` はサーバーが未起動なら自動起動し、ブラウザで開く。`pythonw` 実行なのでコンソール画面（黒い窓）が出ない。

エクスプローラーのファイル関連付けや「送る」に登録すると便利（`.bat` ではなく `pythonw md_open.pyw` を直接ターゲットにすることでフラッシュを防ぐ）。

```bat
:: ファイル関連付け（管理者cmd。.md をすべて本ビューアで開く）
ftype mdpreview="C:\path\to\pythonw.exe" "C:\path\to\md-preview\md_open.pyw" "%1"
assoc .md=mdpreview
```

「送る」に入れる場合は `shell:sendto` に、ターゲット `C:\path\to\pythonw.exe "C:\path\to\md-preview\md_open.pyw"` のショートカットを作成する。

開いたあとは左サイドバーの **Files** タブから、同じリポジトリ内の他の `.md` へワンクリックで移動できる。

### ブラウザから直接アクセス

```
http://localhost:3030/view?path=C:/path/to/file.md
```

### 動作確認

```bash
python md_server.py
# http://localhost:3030/view?path=C:/path/to/file.md でアクセス
```

## ポート変更

デフォルトは `3030`。`config.py` の `DEFAULT_PORT` を変更すれば `md_server.py` と `md_open.pyw` の両方に反映される。
