# md-preview

ローカルのMarkdownファイルをブラウザでプレビューするPythonサーバー。  
複数テーマ対応 + highlight.jsコードハイライト。ファイル変更時に自動リロード。

## 機能

- **複数テーマ**: 8種のダーク系プリセットテーマをドロップダウンで切替
- **カラーインポート**: [iTerm2 Color Schemes](https://iterm2colorschemes.com/) の `.itermcolors` XMLを貼り付けてカスタムテーマを作成
- **見出し色カスタマイズ**: インポートしたパレットからH1〜H4の色を個別選択（シャッフルボタン付き）
- **レイアウト設定**: 箇条書き後マージン・最大横幅をスライダーで調整
- **ミニマップ**: 画面右端にVSCodeスタイルのミニマップ表示（クリック/ドラッグでスクロール）
- **自動リロード**: ファイル変更をMD5ポーリングで検知し自動更新
- **設定永続化**: すべての設定をlocalStorageに保存

## 必要なもの

- Python 3.10+
- `markdown` パッケージ
- [NSSM](https://nssm.cc/)（オプション: Windowsサービス化する場合）

## セットアップ

```bash
git clone https://github.com/kloir-z/md-preview.git
cd md-preview
pip install -r requirements.txt
```

> **Note:** 依存が `markdown` 1パッケージのみのため、venvは使わずグローバルインストールで運用している。

## 使い方

### バッチファイルで開く

```bash
md_open.bat path/to/file.md
```

エクスプローラーの「送る」やファイル関連付けに `md_open.bat` を登録すると便利。  
サーバーが未起動の場合は自動で起動する。

### ブラウザから直接アクセス

```
http://localhost:3030/view?path=C:/path/to/file.md
```

### 動作確認

```bash
python md_server.py
# http://localhost:3030/view?path=C:/path/to/file.md でアクセス
```

## オプション: Windowsサービス化（NSSM）

常時起動が必要な場合はNSSMでサービス登録できる。  
通常は `md_open.bat` がサーバーをオンデマンド起動するため不要。

<details>
<summary>NSSM セットアップ手順</summary>

管理者権限のPowerShellで実行。Pythonパスとリポジトリパスは環境に合わせて変更すること。

```powershell
# Pythonパスを確認
(Get-Command python).Source  # 例: C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe

# サービス登録
nssm install md-preview "C:\path\to\python.exe"
nssm set md-preview AppParameters "C:\path\to\md-preview\md_server.py --port 3030"
nssm set md-preview AppDirectory "C:\path\to\md-preview"
nssm set md-preview DisplayName "Markdown Preview"
nssm set md-preview Description "Local Markdown preview server on port 3030"
nssm set md-preview Start SERVICE_AUTO_START
nssm start md-preview
```

### サービス管理

```powershell
nssm status md-preview
nssm restart md-preview
nssm stop md-preview
nssm remove md-preview confirm  # 削除
```

</details>

## ポート変更

デフォルトは `3030`。`config.py` の `DEFAULT_PORT` を変更すれば `md_server.py` と `md_open.pyw` の両方に反映される。  
NSSMで `--port` 引数を指定している場合は `AppParameters` も合わせて更新すること。
