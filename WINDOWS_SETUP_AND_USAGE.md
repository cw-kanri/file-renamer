# Windows初心者向け 環境構築と実行方法（uv版）

この手順は、Windows TerminalまたはPowerShellで実行する前提です。

このツールでは、Python環境とライブラリ管理を `uv` に統一します。`python -m venv` や `pip install` は使いません。

## 1. 必要なもの

- Windows PC
- uv
- このツールのフォルダ一式

## 2. uvが入っているか確認する

Windows TerminalまたはPowerShellを開き、次を入力します。

```powershell
uv --version
```

バージョンが表示されればOKです。

## 3. uvをインストールする

`uv --version` でエラーになる場合は、uvをインストールします。

PowerShellで次を実行します。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストール後、Windows TerminalまたはPowerShellをいったん閉じて、もう一度開きます。

もう一度確認します。

```powershell
uv --version
```

## 4. ツールのフォルダを開く

このツールのフォルダへ移動します。

例:

```powershell
cd "C:\Users\インターン）奥谷豊\file-renamer"
```

移動できたか確認します。

```powershell
dir
```

`file_renamer.py`、`requirements.txt`、`inputs`、`outputs`、`logs` が表示されればOKです。

## 5. uvで仮想環境を作る

次のコマンドで、このフォルダ専用のPython環境を作ります。

```powershell
uv venv
```

成功すると `.venv` フォルダが作成されます。

この手順では、仮想環境を手動で有効化する必要はありません。以降は `uv run` を使って実行します。

## 6. 必要なライブラリを入れる

`requirements.txt` に書かれているライブラリを、uvでインストールします。

```powershell
uv pip install -r requirements.txt
```

これで `pandas` と `openpyxl` が入ります。

## 7. 入力ファイルを置く

SharePointからエクスポートしたCSVまたはExcelを `inputs/` フォルダに置きます。

Excelファイルが1つだけなら自動で読み込みます。

Excelファイルが2つ以上ある場合は、実行時にどのファイルを使うか番号で選べます。

入力ファイルには、少なくとも次のカラムが必要です。

```text
名前
更新日時
パス
```

サイズ0の除外も使いたい場合は、次のようなサイズ列もあると判定できます。

```text
サイズ
size
Size
file_size
FileSize
```

## 8. サンプルデータで試す

まずはサンプルCSVを作れます。

```powershell
uv run python file_renamer.py --create-sample
```

作成されるファイル:

```text
inputs/sample_sharepoint_files.csv
```

サンプルで一覧を作ります。

```powershell
uv run python file_renamer.py inputs\sample_sharepoint_files.csv
```

出力されるファイル:

```text
outputs/YYYYMMDD_HHMMSS/renamed_file_list.xlsx
outputs/YYYYMMDD_HHMMSS/rename_preview.csv
outputs/YYYYMMDD_HHMMSS/folder_rename_preview.csv
outputs/YYYYMMDD_HHMMSS/content_analysis_candidates.csv
outputs/YYYYMMDD_HHMMSS/rename.log
```

`YYYYMMDD_HHMMSS` は実行時刻です。例: `20260618_153012`

## 9. 実データで一覧を作る

`inputs/` フォルダにSharePoint一覧Excelを置いたら、次を実行します。

```powershell
uv run python file_renamer.py
```

Excelファイルが1つだけなら、自動で選ばれます。

Excelファイルが2つ以上ある場合は、次のように番号選択が表示されます。

```text
inputsフォルダに複数の入力ファイルがあります。使用するファイルを番号で選んでください。
1: sharepoint_files_1.xlsx
2: sharepoint_files_2.xlsx
番号を入力してEnterを押してください:
```

使いたいファイルの番号を入力してEnterを押します。

出力された `outputs/YYYYMMDD_HHMMSS/renamed_file_list.xlsx` を開いて、新しいファイル名が想定どおりか確認してください。

フォルダー名の候補だけ確認したい場合は、次を開きます。

```text
outputs/YYYYMMDD_HHMMSS/folder_rename_preview.csv
```

## 10. 入力ファイルを指定して実行する

自動選択ではなく、ファイルを指定して実行することもできます。

```powershell
uv run python file_renamer.py inputs\sharepoint_files.xlsx
```

CSVを指定する場合:

```powershell
uv run python file_renamer.py inputs\sharepoint_files.csv
```

この場合も、実ファイル名の変更は行いません。

## 11. 出力先を変えたい場合

通常は `outputs/YYYYMMDD_HHMMSS/` に実行ごとのフォルダが作られ、その中に出力されます。必要に応じて、出力フォルダや出力先を指定できます。

実行結果をまとめるフォルダを指定する場合:

```powershell
uv run python file_renamer.py --output-dir outputs\test_run_001
```

整理済み一覧Excelの出力先を変える場合:

```powershell
uv run python file_renamer.py --renamed-list-output outputs\test_run_001\renamed_file_list_test.xlsx
```

プレビューCSVの出力先を変える場合:

```powershell
uv run python file_renamer.py inputs\sharepoint_files.csv --output outputs\test_run_001\preview_test.csv
```

中身解析候補CSVの出力先を変える場合:

```powershell
uv run python file_renamer.py inputs\sharepoint_files.csv --analysis-output outputs\test_run_001\analysis_test.csv
```

フォルダー名変更候補CSVの出力先を変える場合:

```powershell
uv run python file_renamer.py inputs\sharepoint_files.csv --folder-output outputs\test_run_001\folder_test.csv
```

ログの出力先を変える場合:

```powershell
uv run python file_renamer.py inputs\sharepoint_files.csv --log outputs\test_run_001\test.log
```

## 12. よくあるエラー

### `uv` が見つからない

uvがインストールされていないか、インストール後にTerminalを開き直していません。

次を実行して、Terminalを開き直してください。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### `ModuleNotFoundError: No module named 'pandas'`

ライブラリが未インストールです。ツールのフォルダで次を実行してください。

```powershell
uv pip install -r requirements.txt
```

### 必須カラムが不足しています

入力CSV/Excelに `名前`、`更新日時`、`パス` のいずれかがありません。列名を確認してください。

### `inputs\sample_sharepoint_files.csv` が見つからない

先にサンプルCSVを作成してください。

```powershell
uv run python file_renamer.py --create-sample
```

### 入力ファイルが複数あって迷う

`uv run python file_renamer.py` を実行すると番号選択が表示されます。使いたいファイル名の番号を入力してください。

### `uv pip install` でエラーになる

`.venv` がまだ作成されていない可能性があります。先に次を実行してください。

```powershell
uv venv
```

その後、もう一度ライブラリを入れます。

```powershell
uv pip install -r requirements.txt
```

## 13. 作業後の確認

出力結果は次を確認します。

```text
outputs/YYYYMMDD_HHMMSS/renamed_file_list.xlsx
outputs/YYYYMMDD_HHMMSS/rename_preview.csv
outputs/YYYYMMDD_HHMMSS/folder_rename_preview.csv
```

中身解析候補は次を確認します。

```text
outputs/YYYYMMDD_HHMMSS/content_analysis_candidates.csv
```

ログは次を確認します。

```text
outputs/YYYYMMDD_HHMMSS/rename.log
```
