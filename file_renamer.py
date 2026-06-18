from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


BUSINESS_RULES = {
    "給与": ["給与", "タイムカード"],
    "経費": ["経費", "請求書", "銀行", "カード"],
    "統計調査": ["統計", "法人企業統計調査"],
}

FILE_TYPE_RULES = {
    "元データ": ["生データ", "raw", "input"],
    "加工": ["集計", "算出", "加工"],
    "出力": ["送付用", "提出", "final"],
    "マニュアル": ["マニュアル", "readme"],
}

STATUS_RULES = {
    "raw": ["生データ", "raw", "input"],
    "working": ["集計", "算出", "加工"],
    "final": ["送付用", "提出", "final"],
}

EXCLUDED_EXTENSIONS = {".json", ".log"}
SYSTEM_FILE_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
LOW_CONFIDENCE_THRESHOLD = 0.55
DEFAULT_INPUT_DIR = Path("inputs")
DEFAULT_OUTPUT_DIR = Path("outputs")
DEFAULT_LOG_DIR = Path("logs")


@dataclass(frozen=True)
class Decision:
    value: str
    reason: str
    matched_keyword: str | None = None
    confidence: float = 0.0


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def combined_text(name: str, path: str) -> str:
    return f"{name} {path}".lower()


def match_keyword(text: str, rules: dict[str, list[str]], default: str = "その他") -> Decision:
    lowered = text.lower()
    for value, keywords in rules.items():
        for keyword in keywords:
            if keyword.lower() in lowered:
                return Decision(
                    value=value,
                    reason=f"キーワード「{keyword}」に一致",
                    matched_keyword=keyword,
                    confidence=1.0,
                )
    return Decision(value=default, reason="該当キーワードなし", confidence=0.0)


def infer_business_category(name: str, path: str) -> Decision:
    return match_keyword(combined_text(name, path), BUSINESS_RULES)


def infer_file_type(name: str, path: str) -> Decision:
    return match_keyword(combined_text(name, path), FILE_TYPE_RULES)


def infer_status(name: str, path: str) -> Decision:
    decision = match_keyword(combined_text(name, path), STATUS_RULES, default="unknown")
    if decision.value == "unknown":
        return Decision(value="unknown", reason="状態キーワードなし", confidence=0.0)
    return decision


def parse_updated_at(value: object) -> pd.Timestamp | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed


def extract_year_month(name: str, updated_at: object) -> tuple[str, str, float]:
    updated = parse_updated_at(updated_at)

    patterns = [
        (r"(?<!\d)(20\d{2})[-_/年.]?([01]?\d)(?:月)?(?!\d)", "ファイル名の日付表現"),
        (r"(?<!\d)(20\d{2})([01]\d)(?!\d)", "ファイル名のYYYYMM表現"),
    ]
    for pattern, reason in patterns:
        match = re.search(pattern, name)
        if not match:
            continue
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}", reason, 1.0

    month_match = re.search(r"(?<!\d)(1[0-2]|0?[1-9])月", name)
    if month_match and updated is not None:
        month = int(month_match.group(1))
        return f"{updated.year:04d}-{month:02d}", "ファイル名の日本語月表現 + 更新日時の年", 0.8

    if updated is not None:
        return f"{updated.year:04d}-{updated.month:02d}", "更新日時から抽出", 0.65

    return "unknown", "年月を抽出できません", 0.0


def is_zero_size(row: pd.Series) -> bool:
    for column in ("サイズ", "size", "Size", "file_size", "FileSize"):
        if column in row and not pd.isna(row[column]):
            try:
                return float(row[column]) == 0
            except (TypeError, ValueError):
                return False
    return False


def is_system_file(name: str) -> bool:
    lowered = name.lower()
    return lowered in SYSTEM_FILE_NAMES or lowered.startswith("~$")


def should_exclude(row: pd.Series, name: str, path: str) -> tuple[bool, str]:
    suffix = Path(name).suffix.lower()
    text = combined_text(name, path)

    if "~bromium" in path.lower():
        return True, "~BROMIUMを含むパス"
    if suffix in EXCLUDED_EXTENSIONS:
        return True, f"対象外拡張子（{suffix}）"
    if "audit" in text or "監査" in text:
        return True, "audit系ファイル"
    if is_zero_size(row):
        return True, "サイズ0"
    if is_system_file(name):
        return True, "システムファイル"
    return False, ""


def sanitize_component(value: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\r\n\t]', "_", value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "unknown"


def looks_meaningless(name: str) -> bool:
    stem = Path(name).stem
    if len(stem.strip()) <= 2:
        return True
    if re.fullmatch(r"[\W_]+", stem, flags=re.UNICODE):
        return True
    if re.fullmatch(r"\d{6,}", stem):
        return True
    return False


def build_new_name(
    business: str,
    file_type: str,
    year_month: str,
    status: str,
    original_name: str,
) -> str:
    parts = [business, file_type, year_month, status]
    prefix = "_".join(sanitize_component(part) for part in parts)
    return f"{prefix}_{sanitize_component(original_name)}"


def confidence_score(
    business: Decision,
    file_type: Decision,
    status: Decision,
    year_month_confidence: float,
) -> float:
    weights = {
        "business": 0.35,
        "file_type": 0.25,
        "status": 0.15,
        "year_month": 0.25,
    }
    score = (
        business.confidence * weights["business"]
        + file_type.confidence * weights["file_type"]
        + status.confidence * weights["status"]
        + year_month_confidence * weights["year_month"]
    )
    return round(min(max(score, 0.0), 1.0), 2)


def make_preview_row(row: pd.Series) -> dict[str, object]:
    name = normalize_text(row.get("名前"))
    path = normalize_text(row.get("パス"))
    updated_at = row.get("更新日時")

    excluded, exclude_reason = should_exclude(row, name, path)
    business = infer_business_category(name, path)
    file_type = infer_file_type(name, path)
    status = infer_status(name, path)
    year_month, year_month_reason, year_month_conf = extract_year_month(name, updated_at)

    new_name = ""
    score = confidence_score(business, file_type, status, year_month_conf)
    meaningless = looks_meaningless(name)
    unknowns = [
        label
        for label, value in (
            ("業務分類", business.value),
            ("ファイル種別", file_type.value),
            ("年月", year_month),
            ("状態", status.value),
        )
        if value in {"その他", "unknown"}
    ]
    needs_content_analysis = bool(unknowns or score < LOW_CONFIDENCE_THRESHOLD or meaningless)

    if not excluded:
        new_name = build_new_name(business.value, file_type.value, year_month, status.value, name)

    reason = (
        f"業務分類: {business.reason}; "
        f"種別: {file_type.reason}; "
        f"状態: {status.reason}; "
        f"年月: {year_month_reason}"
    )

    return {
        "old_name": name,
        "new_name": new_name,
        "path": path,
        "判定理由": reason,
        "business_category": business.value,
        "file_type": file_type.value,
        "year_month": year_month,
        "status": status.value,
        "excluded": excluded,
        "exclude_reason": exclude_reason,
        "needs_content_analysis": needs_content_analysis,
        "confidence_score": score,
        "analysis_reason": ", ".join(unknowns + (["意味不明なファイル名"] if meaningless else [])),
    }


def load_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    raise ValueError("入力ファイルは .csv / .xlsx / .xls に対応しています")


def validate_columns(df: pd.DataFrame) -> None:
    required = {"名前", "更新日時", "パス"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"必須カラムが不足しています: {', '.join(sorted(missing))}")


def create_preview(df: pd.DataFrame) -> pd.DataFrame:
    validate_columns(df)
    return pd.DataFrame(make_preview_row(row) for _, row in df.iterrows())


def source_file_path(path_value: str, old_name: str) -> Path:
    path = Path(path_value)
    if path.name == old_name:
        return path
    return path / old_name


def rename_file(old_path: Path, new_name: str, dry_run: bool = True) -> tuple[bool, str]:
    new_path = old_path.with_name(new_name)
    if dry_run:
        return True, f"dry-run: {old_path} -> {new_path}"
    if not old_path.exists():
        return False, f"元ファイルが存在しません: {old_path}"
    if new_path.exists():
        return False, f"同名ファイルが既に存在します: {new_path}"
    try:
        old_path.rename(new_path)
        return True, f"renamed: {old_path} -> {new_path}"
    except OSError as exc:
        return False, f"リネーム失敗: {old_path} -> {new_path}: {exc}"


def execute_renames(preview: pd.DataFrame, dry_run: bool = True) -> pd.DataFrame:
    results: list[dict[str, object]] = []
    targets = preview[~preview["excluded"]].copy()

    for _, row in targets.iterrows():
        old_path = source_file_path(str(row["path"]), str(row["old_name"]))
        ok, message = rename_file(old_path, str(row["new_name"]), dry_run=dry_run)
        log = logging.info if ok else logging.error
        log(message)
        results.append(
            {
                "old_name": row["old_name"],
                "new_name": row["new_name"],
                "path": row["path"],
                "success": ok,
                "message": message,
            }
        )

    return pd.DataFrame(results)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def create_sample_csv(path: Path) -> None:
    sample = pd.DataFrame(
        [
            {
                "名前": "202603_タイムカード_生データ.xlsx",
                "更新日時": "2026-03-31 18:20:00",
                "パス": r"C:\SharePoint\給与\2026",
                "サイズ": 2048,
            },
            {
                "名前": "MF取込_final.csv",
                "更新日時": "2026-03-31",
                "パス": r"C:\SharePoint\給与\送付用",
                "サイズ": 1024,
            },
            {
                "名前": "3月_請求書_集計.xlsx",
                "更新日時": "2026-04-02",
                "パス": r"C:\SharePoint\経費\銀行カード",
                "サイズ": 4096,
            },
            {
                "名前": "法人企業統計調査_提出_202604.xlsx",
                "更新日時": "2026-04-15",
                "パス": r"C:\SharePoint\統計",
                "サイズ": 5120,
            },
            {
                "名前": "123456789.xlsx",
                "更新日時": "2026-05-01",
                "パス": r"C:\SharePoint\不明",
                "サイズ": 128,
            },
            {
                "名前": "audit.log",
                "更新日時": "2026-05-01",
                "パス": r"C:\SharePoint\logs",
                "サイズ": 128,
            },
        ]
    )
    write_csv(sample, path)


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SharePointファイル名リネームプレビュー作成ツール")
    parser.add_argument("input", nargs="?", type=Path, help="SharePointからエクスポートしたCSV/Excel")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "rename_preview.csv",
        help="プレビューCSVの出力先",
    )
    parser.add_argument(
        "--analysis-output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "content_analysis_candidates.csv",
        help="中身解析候補CSVの出力先",
    )
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_DIR / "rename.log", help="ログファイルの出力先")
    parser.add_argument("--execute", action="store_true", help="実際にファイル名を変更します（指定なしはdry-run）")
    parser.add_argument(
        "--create-sample",
        nargs="?",
        const=DEFAULT_INPUT_DIR / "sample_sharepoint_files.csv",
        type=Path,
        help="サンプルCSVを作成して終了します。パス省略時は inputs/sample_sharepoint_files.csv",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log)

    if args.create_sample:
        create_sample_csv(args.create_sample)
        logging.info("サンプルCSVを作成しました: %s", args.create_sample)
        return 0

    if not args.input:
        logging.error("入力ファイルを指定してください。例: python file_renamer.py input.csv")
        return 2

    try:
        df = load_input(args.input)
        preview = create_preview(df)
        write_csv(preview, args.output)

        candidates = preview[preview["needs_content_analysis"]].copy()
        write_csv(candidates, args.analysis_output)

        results = execute_renames(preview, dry_run=not args.execute)
        if not results.empty:
            result_path = args.output.parent / "rename_results.csv"
            write_csv(results, result_path)
            logging.info("リネーム結果を出力しました: %s", result_path)

        logging.info("プレビューを出力しました: %s", args.output)
        logging.info("中身解析候補を出力しました: %s", args.analysis_output)
        logging.info("モード: %s", "execute" if args.execute else "dry-run")
        return 0
    except Exception as exc:
        logging.exception("処理に失敗しました: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
