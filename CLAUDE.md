# CLAUDE.md

> **CLAUDE.md編集ポリシー**: このファイルは最小限に保つ。内容を追加・修正する前に、参照先ドキュメント（docs/ 等）に書くべきかユーザーに確認すること。

## Project overview

Markdown Preview Server -- ローカルのMarkdownファイルをブラウザでプレビューするPythonサーバー。ファイル変更時にポーリングで自動リロード。Monokaiテーマ。ポート3030で動作。

## Architecture

- `md_server.py` -- HTTPサーバー本体。`markdown`ライブラリでHTML変換、highlight.jsでコードハイライト。MD5ハッシュによるポーリングで変更検知・自動リロード。
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
