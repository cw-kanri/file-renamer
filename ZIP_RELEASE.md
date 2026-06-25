# ZIP化リリース手順

この手順は、ツールをZIPファイルとして配布するための手順です。

目的は、コードと説明書だけを配布し、実データ・出力結果・ログ・キャッシュをZIPに入れないことです。

## 配布に含めるもの

ZIPに含めるファイル:

```text
file_renamer.py
requirements.txt
README.md
WINDOWS_SETUP_AND_USAGE.md
ZIP_RELEASE.md
.gitignore
inputs/.gitkeep
outputs/.gitkeep
logs/.gitkeep
```

ZIPに含めないもの:

```text
inputs/*.csv
inputs/*.xlsx
outputs/*
logs/*
__pycache__/
.venv/
.git/
```

## 1. 作業ツリーを確認する

Git管理している場合は、まず状態を確認します。

```powershell
git status --short --ignored
```

`inputs/`、`outputs/`、`logs/` の実データや生成物が `!!` と表示されていれば、ignore対象になっています。

追跡対象ファイルだけを確認します。

```powershell
git ls-files
```

この一覧に実データ、ログ、出力CSV、`__pycache__` が含まれていないことを確認してください。

## 2. リリース用フォルダを作る

PowerShellでツールのルートフォルダにいる状態で実行します。

```powershell
$releaseDir = "release\file-renamer"
New-Item -ItemType Directory -Force $releaseDir
New-Item -ItemType Directory -Force "$releaseDir\inputs"
New-Item -ItemType Directory -Force "$releaseDir\outputs"
New-Item -ItemType Directory -Force "$releaseDir\logs"
```

## 3. 必要なファイルだけコピーする

```powershell
Copy-Item file_renamer.py $releaseDir
Copy-Item requirements.txt $releaseDir
Copy-Item README.md $releaseDir
Copy-Item WINDOWS_SETUP_AND_USAGE.md $releaseDir
Copy-Item ZIP_RELEASE.md $releaseDir
Copy-Item .gitignore $releaseDir
Copy-Item inputs\.gitkeep "$releaseDir\inputs"
Copy-Item outputs\.gitkeep "$releaseDir\outputs"
Copy-Item logs\.gitkeep "$releaseDir\logs"
```

## 4. ZIPを作成する

既存のZIPがある場合は削除してから作ります。

```powershell
$zipPath = "release\file-renamer.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath
}
Compress-Archive -Path $releaseDir -DestinationPath $zipPath
```

作成されるZIP:

```text
release/file-renamer.zip
```

## 5. ZIPの中身を確認する

```powershell
Expand-Archive -Path release\file-renamer.zip -DestinationPath release\check -Force
dir release\check\file-renamer
```

次のものが入っていないことを確認します。

- 実データのCSV/Excel
- `rename_preview.csv`
- `renamed_file_list.xlsx`
- `folder_rename_preview.csv`
- `content_analysis_candidates.csv`
- `rename.log`
- `.git`
- `.venv`
- `__pycache__`

## 6. GitHub Releasesに載せる場合

1. GitHubでこのリポジトリを開く
2. `Releases` を開く
3. `Draft a new release` を選ぶ
4. タグ名を入力する

例:

```text
v0.1.0
```

5. タイトルを入力する

例:

```text
file-renamer v0.1.0
```

6. `release/file-renamer.zip` を添付する
7. 説明に変更点を書く
8. `Publish release` を押す

## 7. リリース前チェックリスト

- `README.md` が最新
- `WINDOWS_SETUP_AND_USAGE.md` の実行コマンドが最新
- `requirements.txt` が最新
- `git ls-files` に実データや出力物が含まれていない
- ZIPの中に `.git`、`.venv`、`__pycache__` がない
- ZIPを展開してサンプル実行できる

## 8. ZIP展開後の動作確認

確認用にZIPを展開したフォルダで、次を実行します。

```powershell
uv venv
uv pip install -r requirements.txt
uv run python file_renamer.py --create-sample
uv run python file_renamer.py inputs\sample_sharepoint_files.csv
```

`outputs/YYYYMMDD_HHMMSS/renamed_file_list.xlsx`、`outputs/YYYYMMDD_HHMMSS/rename_preview.csv`、`outputs/YYYYMMDD_HHMMSS/folder_rename_preview.csv` が作成されれば、配布ZIPとして最低限の動作確認は完了です。
