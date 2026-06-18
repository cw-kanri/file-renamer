# SharePoint File Renamer

SharePointからエクスポートしたファイル一覧をもとに、検索しやすいファイル名を自動生成するPythonツールです。

SharePointから出力した一覧Excel/CSVそのもののファイル名を変えるツールではありません。一覧ファイルの中に書かれている各ファイル行に対して、新しいファイル名と新しいパスを追加したExcelを出力します。

元のファイル名は `旧ファイル名` として残します。実ファイル名の変更は行いません。

## できること

- SharePointのファイル一覧CSV/Excelを読み込み
- `inputs/` フォルダから入力Excelを自動検出
- 入力ファイルが複数ある場合はCLIで選択
- ファイル名とパスから業務分類を推定
- ファイル名とパスからファイル種別を推定
- ファイル名または更新日時から年月を抽出
- ファイル状態を `raw` / `working` / `final` / `unknown` に分類
- 旧ファイル名を残したまま、新ファイル名と新パスを追加したExcelを出力
- 新しいファイル名のプレビューCSVを出力
- リネーム対象外ファイルを除外
- 判定不能・低信頼度・意味不明なファイル名を中身解析候補として別出力
- ログを出力

## 命名ルール

新しいファイル名は次の形式で生成します。

```text
[業務分類]_[ファイル種別]_[年月]_[状態]_[元ファイル名]
```

例:

```text
給与_元データ_2026-03_raw_タイムカード.xlsx
給与_出力_2026-03_final_MF取込.csv
```

## 判定ルール

### 業務分類

| 判定結果 | キーワード |
| --- | --- |
| 給与 | 給与、タイムカード |
| 経費 | 経費、請求書、銀行、カード |
| 統計調査 | 統計、法人企業統計調査 |
| その他 | 上記以外 |

### ファイル種別

| 判定結果 | キーワード |
| --- | --- |
| 元データ | 生データ、raw、input |
| 加工 | 集計、算出、加工 |
| 出力 | 送付用、提出、final |
| マニュアル | マニュアル、readme |
| その他 | 上記以外 |

### 年月

次の順で `YYYY-MM` 形式に統一します。

1. ファイル名の日付表現
2. ファイル名の `YYYYMM` 表現
3. `3月` などの日本語月表現と更新日時の年
4. 更新日時
5. 抽出不能な場合は `unknown`

### 状態

| 判定結果 | キーワード |
| --- | --- |
| raw | 生データ、raw、input |
| working | 集計、算出、加工 |
| final | 送付用、提出、final |
| unknown | 上記以外 |

## 除外対象

次のファイルはリネーム対象外として扱います。

- パスに `~BROMIUM` を含む
- `.json` / `.log`
- `audit` または `監査` を含む
- サイズが0
- `desktop.ini`、`Thumbs.db`、`.DS_Store`
- Excelなどの一時ファイルと思われる `~$` 始まりのファイル

## 出力ファイル

| ファイル | 内容 |
| --- | --- |
| `outputs/YYYYMMDD_HHMMSS/renamed_file_list.xlsx` | 元の一覧に旧ファイル名、新ファイル名、新パス、判定情報を追加したExcel |
| `outputs/YYYYMMDD_HHMMSS/rename_preview.csv` | 新旧ファイル名、パス、判定理由、信頼度など |
| `outputs/YYYYMMDD_HHMMSS/content_analysis_candidates.csv` | 中身解析候補だけを抽出したCSV |
| `outputs/YYYYMMDD_HHMMSS/rename.log` | 実行ログ |

通常実行では、実行時刻ごとに `outputs/YYYYMMDD_HHMMSS/` フォルダを自動作成します。過去の試行結果は上書きされません。

## フォルダ構成

```text
file-renamer/
  file_renamer.py
  requirements.txt
  README.md
  WINDOWS_SETUP_AND_USAGE.md
  ZIP_RELEASE.md
  inputs/
  outputs/
  logs/
```

`inputs/`、`outputs/`、`logs/` の中身は `.gitignore` で除外しています。実データや生成物を誤ってGitに含めないためです。

## 詳しい使い方

Windowsでの環境構築と実行方法は [WINDOWS_SETUP_AND_USAGE.md](WINDOWS_SETUP_AND_USAGE.md) を参照してください。

ZIP配布用ファイルの作成手順は [ZIP_RELEASE.md](ZIP_RELEASE.md) を参照してください。
