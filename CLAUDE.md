# CLAUDE.md

> **CLAUDE.md編集ポリシー**: このファイルは最小限に保つ。内容を追加・修正する前に、参照先ドキュメント（docs/ 等）に書くべきかユーザーに確認すること。

## 行動指針

- **サーバー再起動**: `md_server.py` を変更した場合、動作確認のため起動中のサーバープロセス（`pythonw md_server.py`）を再起動する。Windowsサービスとしては登録していない（`md_open.pyw` がオンデマンド起動する）。
- **コミット・プッシュ**: コード変更やドキュメント更新を行った後は、コミットとプッシュが必要かユーザーに確認すること。

## Project overview

Markdown Preview Server -- ローカルのMarkdownファイルをブラウザでプレビューするPythonサーバー。ファイル変更時にポーリングで自動リロード。複数テーマ対応 + カスタムカラーインポート。ポート3030で動作。

## Architecture

- `config.py` -- 共通設定（`DEFAULT_PORT`等）。`md_server.py`と`md_open.pyw`から参照。
- `md_server.py` -- HTTPサーバー本体。`HTML_TEMPLATE`内にCSS/HTML/JSをすべて含む。`markdown`ライブラリでHTML変換、highlight.jsでコードハイライト。MD5ハッシュによるポーリングで変更検知・自動リロード。
  - **テーマ**: 8種のダーク系プリセット + .itermcolorsカラーインポートによるカスタムテーマ。CSS変数ベース。
  - **サイドバー**: 左側にOutline（見出し目次・スクロール追従ハイライト）とFiles（`.md`フォルダツリー。走査ルートはgitリポジトリ内ならリポジトリのトップ階層、git管理外なら開いたファイルのフォルダ。そのルート以下をファイルシステム走査し、追跡/未追跡・`.gitignore`問わず全`.md`を列挙。`.git`/`node_modules`等は除外）のタブ。ファイル/フォルダはSVGアイコンで識別（フォルダは見出し色で強調）。Filesのファイルクリックで右ペイン（`#mdContent`）を`/render`でAjax差し替え（フルリロードせず、mermaid/hljsを再利用）。URL（`history.pushState`）・タイトル・アウトライン・ミニマップ・選択ハイライトを追従更新。ツリーの展開状態は維持。開いているファイルを含むフォルダは折り畳み時に行をハイライト（祖先フォルダに`has-active`付与）。右端のドラッグハンドルで幅変更（`--toc-width`）。
  - **ミニマップ**: 画面右端にVSCodeスタイルのミニマップ（CSS Transform方式でDOMクローンを縮小表示）。クリック/ドラッグでスクロール。左端のドラッグハンドルで幅変更（`--minimap-width`、設定スライダーと同期）。
  - **設定モーダル**: テーマ選択（ドロップダウン）、コードテーマ選択（シンタックスハイライト、`hljs/`の8種から切替。アプリテーマとは独立。背景は`--code-bg`に統一しトークン色のみ反映）、カラーインポート（.itermcolors XML貼り付け）、本文色（`--fg`）・見出し色（H1-H4）カスタマイズ（パレットから選択、見出しはシャッフル可。`--fg`はテーマ切替後も`applyUserColors`で維持）、レイアウト設定（箇条書きマージン・最大横幅・ミニマップ幅スライダー）。
  - **永続化**: すべての設定（テーマ・色・レイアウト・サイドバー幅/開閉/タブ・ミニマップ幅）をlocalStorageに保存、ページロード時に即座に適用。
- `md_open.pyw` -- Markdownファイルオープナー。サーバーが未起動なら自動起動し、ブラウザで開く。`pythonw`実行のためコンソール画面が出ない。ファイル関連付け・「送る」のターゲットにする（例: `pythonw md_open.pyw "%1"`）。
- `static/` -- highlight.min.js、`hljs/`配下にシンタックスハイライト用テーマ8種（GitHub Dark/Atom One Dark/Tokyo Night Dark/Monokai/Dracula/Nord/VS2015/a11y Dark、デフォルトGitHub Dark）、mermaid.min.js（ローカル配置）。

## Endpoints

- `GET /view?path=<filepath>` -- MarkdownをHTMLレンダリングして表示
- `GET /hash?path=<filepath>` -- ファイルのMD5ハッシュを返す（自動リロード用）
- `GET /content?path=<filepath>` -- ファイルの生テキストを返す（編集モード用）
- `GET /render?path=<filepath>` -- レンダリング済みHTML断片+ハッシュ+タイトルをJSONで返す（シームレスなファイル切替・自動リロード用）
- `GET /files?path=<filepath>` -- そのファイル周辺の`.md`一覧をJSONで返す（サイドバーのFilesタブ用）。走査ルートはgitリポジトリ内ならリポジトリのトップ階層（`git rev-parse --show-toplevel`）、git管理外なら開いたファイルのフォルダ。そのルート以下をファイルシステム走査し、追跡/未追跡・`.gitignore`問わず全`.md`を列挙（`.git`/`node_modules`等は除外、上限1000件）。
- `GET /open?path=<filepath>` -- `/view`へリダイレクト
- `GET /static/<file>` -- 静的ファイル配信
- `POST /save?path=<filepath>` -- 編集内容を保存（編集モード用）

## Key decisions

- WebSocketではなくMD5ポーリング（1秒間隔）で変更検知。stdlib依存のみでシンプルに保つ。
- highlight.jsとmonokaiテーマはCDNではなくローカル配置（オフライン動作対応）。
- `md_open.pyw`は`DETACHED_PROCESS`フラグでサーバーをバックグラウンド起動。
- UIはすべて`HTML_TEMPLATE`内に埋め込み（単一ファイル構成）。新規HTMLファイルなし。
- ミニマップはCSS Transform方式（Canvas描画ではない）。テーマ変更に自動追従。
- Files一覧は常にファイルシステム走査（`_scan_dir_markdown`）で取得する。gitは走査ルートの決定にのみ使用（`git -C <dir> rev-parse --show-toplevel`が成功すればリポジトリのトップ階層、失敗すれば開いたファイルのフォルダ）。`git ls-files`は使わない＝追跡/未追跡・`.gitignore`に関係なく全`.md`を出すため。`.git`/`node_modules`等は除外・上限1000件。rel/absは前方スラッシュ表記で返し、`window.__md.path`との選択ハイライト整合を保つ。
- ファイル切替はフルリロードせず`/render`でAjax差し替え（mermaid 3.3MB等の再パースとgit再読込を回避）。現在表示中の状態は`window.__md`で共有。

## Development

```bash
# サーバー起動
python md_server.py [--port 3030]

# ファイルを指定して起動（ブラウザも開く）
python md_server.py path/to/file.md

# オープナー経由（サーバー未起動なら自動起動。コンソール非表示）
pythonw md_open.pyw path/to/file.md
```

依存: `pip install markdown`
