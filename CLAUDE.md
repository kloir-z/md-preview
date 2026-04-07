# CLAUDE.md

> **CLAUDE.md編集ポリシー**: このファイルは最小限に保つ。内容を追加・修正する前に、参照先ドキュメント（docs/ 等）に書くべきかユーザーに確認すること。

## 行動指針

- **サービス再起動**: `md_server.py` を変更した場合、動作確認のためサービスを再起動する。`powershell -Command "Start-Process powershell -ArgumentList '-Command','Restart-Service md-preview' -Verb RunAs"`
- **コミット・プッシュ**: コード変更やドキュメント更新を行った後は、コミットとプッシュが必要かユーザーに確認すること。

## Project overview

Markdown Preview Server -- ローカルのMarkdownファイルをブラウザでプレビューするPythonサーバー。ファイル変更時にポーリングで自動リロード。複数テーマ対応 + カスタムカラーインポート。ポート3030で動作。

## Architecture

- `config.py` -- 共通設定（`DEFAULT_PORT`等）。`md_server.py`と`md_open.pyw`から参照。
- `md_server.py` -- HTTPサーバー本体。`HTML_TEMPLATE`内にCSS/HTML/JSをすべて含む。`markdown`ライブラリでHTML変換、highlight.jsでコードハイライト。MD5ハッシュによるポーリングで変更検知・自動リロード。
  - **テーマ**: 8種のダーク系プリセット + .itermcolorsカラーインポートによるカスタムテーマ。CSS変数ベース。
  - **ミニマップ**: 画面右端にVSCodeスタイルのミニマップ（CSS Transform方式でDOMクローンを縮小表示）。クリック/ドラッグでスクロール。
  - **設定モーダル**: テーマ選択（ドロップダウン）、カラーインポート（.itermcolors XML貼り付け）、見出し色カスタマイズ（H1-H4、パレットから選択+シャッフル）、レイアウト設定（箇条書きマージン・最大横幅スライダー）。
  - **永続化**: すべての設定をlocalStorageに保存、ページロード時に即座に適用。
- `md_open.pyw` -- Markdownファイルオープナー。サーバーが未起動なら自動起動し、ブラウザで開く。
- `md_open.bat` -- `md_open.pyw`のバッチラッパー。右クリック「送る」等から使用。
- `static/` -- highlight.min.js、monokai.min.css（ローカル配置）。

## Endpoints

- `GET /view?path=<filepath>` -- MarkdownをHTMLレンダリングして表示
- `GET /hash?path=<filepath>` -- ファイルのMD5ハッシュを返す（自動リロード用）
- `GET /open?path=<filepath>` -- `/view`へリダイレクト
- `GET /static/<file>` -- 静的ファイル配信

## Key decisions

- WebSocketではなくMD5ポーリング（1秒間隔）で変更検知。stdlib依存のみでシンプルに保つ。
- highlight.jsとmonokaiテーマはCDNではなくローカル配置（オフライン動作対応）。
- `md_open.pyw`は`DETACHED_PROCESS`フラグでサーバーをバックグラウンド起動。
- UIはすべて`HTML_TEMPLATE`内に埋め込み（単一ファイル構成）。新規HTMLファイルなし。
- ミニマップはCSS Transform方式（Canvas描画ではない）。テーマ変更に自動追従。

## Development

```bash
# サーバー起動
python md_server.py [--port 3030]

# ファイルを指定して起動（ブラウザも開く）
python md_server.py path/to/file.md

# バッチから起動
md_open.bat path/to/file.md
```

依存: `pip install markdown`

## Service

NSSMでWindowsサービスとして登録済み。PC起動時に自動起動。

```powershell
# サービス管理（管理者権限が必要）
powershell -Command "Start-Process powershell -ArgumentList '-Command','Restart-Service md-preview' -Verb RunAs"
nssm status md-preview
nssm edit md-preview
```
