from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from zipfile import BadZipFile

from bertopic_cli import __version__


ENGLISH_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MULTILINGUAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

class CLIError(Exception):
    """An error that can be explained without a traceback."""


@dataclass(frozen=True)
class InputData:
    table: Any
    documents: list[str]
    text_columns: list[str]
    skipped_rows: int
    sheet: str | None


def parse_reduce_topics(value: str) -> int | str | None:
    lowered = value.lower()
    if lowered == "none":
        return None
    if lowered == "auto":
        return "auto"
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("none, auto 또는 2 이상의 정수를 입력하세요.") from exc
    if count < 2:
        raise argparse.ArgumentTypeError("주제 수는 2 이상이어야 합니다.")
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bertopic-cli",
        description="CSV/TSV/XLSX 문서를 BERTopic으로 분석합니다.",
        epilog=(
            "예시:\n"
            "  bertopic-cli papers.csv --text-columns abstract\n"
            "  bertopic-cli papers.csv --text-columns title abstract\n"
            "  bertopic-cli reviews.xlsx --sheet 응답 --text-columns review"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="분석할 CSV, TSV 또는 XLSX 파일")
    parser.add_argument(
        "--text-columns",
        nargs="+",
        help="분석할 텍스트 열 이름들. 여러 열은 지정한 순서대로 합칩니다. 분석 실행 시 필수입니다.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="결과 폴더. 기본값: 입력 파일 옆의 <파일명>_bertopic_results",
    )
    parser.add_argument(
        "--sheet",
        help="XLSX에서 읽을 시트 이름. 생략하면 첫 번째 시트를 사용합니다.",
    )
    parser.add_argument(
        "--language",
        choices=("multilingual", "english"),
        default="multilingual",
        help="문서 언어. 한국어 또는 혼합 문서는 multilingual을 사용합니다. 기본값: multilingual",
    )
    parser.add_argument(
        "--embedding-model",
        help="고급 설정: Hugging Face/SentenceTransformers 임베딩 모델 이름",
    )
    parser.add_argument(
        "--min-topic-size",
        type=int,
        help="주제 하나를 만들 최소 문서 수. 생략하면 문서 수에 맞춰 자동 설정합니다.",
    )
    parser.add_argument(
        "--reduce-topics",
        type=parse_reduce_topics,
        default=None,
        metavar="none|auto|N",
        help="비슷한 주제 합치기: none, auto 또는 목표 주제 수 N. 기본값: none",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="결과 재현을 위한 난수값. 기본값: 42",
    )
    parser.add_argument(
        "--save-model",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="학습 모델 저장 여부. 기본값: 저장",
    )
    parser.add_argument(
        "--visualizations",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="HTML 시각화 저장 여부. 기본값: 저장",
    )
    parser.add_argument(
        "--list-columns",
        action="store_true",
        help="입력 파일의 열 이름만 표시하고 종료합니다.",
    )
    parser.add_argument("--quiet", action="store_true", help="BERTopic 진행 로그를 줄입니다.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return re.sub(r"\s+", " ", str(value)).strip()


def read_table(path: Path, sheet: str | None = None) -> Any:
    import pandas as pd

    if not path.exists():
        raise CLIError(f"입력 파일을 찾을 수 없습니다: {path}")
    if not path.is_file():
        raise CLIError(f"입력 경로가 파일이 아닙니다: {path}")

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            if sheet:
                raise CLIError("--sheet 옵션은 XLSX 파일에서만 사용할 수 있습니다.")
            return pd.read_csv(path)
        if suffix in {".tsv", ".tab"}:
            if sheet:
                raise CLIError("--sheet 옵션은 XLSX 파일에서만 사용할 수 있습니다.")
            return pd.read_csv(path, sep="\t")
        if suffix == ".xlsx":
            with pd.ExcelFile(path, engine="openpyxl") as workbook:
                selected_sheet = sheet if sheet else workbook.sheet_names[0]
                table = pd.read_excel(workbook, sheet_name=selected_sheet)
            table.attrs["source_sheet"] = selected_sheet
            return table
    except CLIError:
        raise
    except (OSError, UnicodeError, pd.errors.ParserError, ValueError, BadZipFile) as exc:
        raise CLIError(f"입력 파일을 읽지 못했습니다: {exc}") from exc

    raise CLIError("지원하지 않는 파일 형식입니다. .csv, .tsv, .tab 또는 .xlsx 파일을 사용하세요.")


def validate_columns(columns: Sequence[object], requested: Sequence[str]) -> None:
    names = [str(column) for column in columns]
    missing = [column for column in requested if column not in names]
    if missing:
        missing_text = ", ".join(missing)
        available_text = ", ".join(names)
        raise CLIError(
            f"지정한 열이 입력 파일에 없습니다: {missing_text}. "
            f"사용 가능한 열: {available_text}"
        )


def prepare_input(path: Path, text_columns: Sequence[str], sheet: str | None = None) -> InputData:
    table = read_table(path, sheet)
    validate_columns(table.columns, text_columns)
    cleaned = table.loc[:, list(text_columns)].apply(lambda column: column.map(normalize_text))
    documents = cleaned.apply(
        lambda row: "\n".join(value for value in row if value),
        axis=1,
    )
    usable = documents.ne("")
    filtered = table.loc[usable].copy()
    filtered.insert(0, "source_row", table.index[usable] + 2)
    filtered.loc[:, list(text_columns)] = cleaned.loc[usable]
    document_list = documents.loc[usable].tolist()
    skipped_rows = int((~usable).sum())

    if len(document_list) < 10:
        raise CLIError(
            f"사용 가능한 문서가 {len(document_list)}개뿐입니다. "
            "BERTopic 분석에는 최소 10개, 가능하면 수십~수백 개 문서를 준비하세요."
        )
    return InputData(
        filtered.reset_index(drop=True),
        document_list,
        list(text_columns),
        skipped_rows,
        table.attrs.get("source_sheet"),
    )


def choose_min_topic_size(document_count: int) -> int:
    if document_count < 30:
        return 2
    if document_count < 100:
        return 5
    if document_count < 500:
        return 10
    return min(50, max(10, round(document_count * 0.02)))


def resolve_embedding_model(language: str, requested: str | None) -> str:
    if requested:
        return requested
    if language == "english":
        return ENGLISH_EMBEDDING_MODEL
    return MULTILINGUAL_EMBEDDING_MODEL


def create_topic_model(
    document_count: int,
    language: str,
    embedding_model: str,
    min_topic_size: int,
    reduce_topics: int | str | None,
    random_seed: int,
    verbose: bool,
) -> Any:
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    n_neighbors = max(2, min(15, document_count - 1))
    n_components = min(5, max(2, document_count // 3))
    stop_words = "english" if language == "english" else None

    return BERTopic(
        embedding_model=embedding_model,
        umap_model=UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            min_dist=0.0,
            metric="cosine",
            random_state=random_seed,
        ),
        hdbscan_model=HDBSCAN(
            min_cluster_size=min_topic_size,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        ),
        vectorizer_model=CountVectorizer(
            stop_words=stop_words,
            ngram_range=(1, 2),
            min_df=1,
        ),
        min_topic_size=min_topic_size,
        nr_topics=reduce_topics,
        calculate_probabilities=False,
        verbose=verbose,
    )


def topic_keywords(model: Any, topic: int, limit: int = 10) -> str:
    if topic == -1:
        return ""
    words = model.get_topic(topic) or []
    return ", ".join(str(word) for word, _ in words[:limit])


def topic_label(model: Any, topic: int, limit: int = 4) -> str:
    if topic == -1:
        return "Outlier"
    words = model.get_topic(topic) or []
    label = " / ".join(str(word) for word, _ in words[:limit])
    return label or f"Topic {topic}"


def build_result_tables(model: Any, input_data: InputData, topics: Sequence[int]) -> tuple[Any, Any]:
    import pandas as pd

    unique_topics = sorted(set(int(topic) for topic in topics))
    labels = {topic: topic_label(model, topic) for topic in unique_topics}
    keywords = {topic: topic_keywords(model, topic) for topic in unique_topics}

    documents = input_data.table.copy()
    documents["topic"] = [int(topic) for topic in topics]
    documents["topic_label"] = documents["topic"].map(labels)
    documents["topic_keywords"] = documents["topic"].map(keywords)

    topic_info = model.get_topic_info()
    summaries: list[dict[str, object]] = []
    for row in topic_info.itertuples(index=False):
        topic = int(getattr(row, "Topic"))
        summaries.append(
            {
                "topic": topic,
                "document_count": int(getattr(row, "Count")),
                "topic_label": labels.get(topic, topic_label(model, topic)),
                "topic_keywords": keywords.get(topic, topic_keywords(model, topic)),
                "is_outlier": topic == -1,
            }
        )
    return documents, pd.DataFrame(summaries)


def default_output_dir(input_path: Path) -> Path:
    return input_path.parent / f"{input_path.stem}_bertopic_results"


def save_model(model: Any, output_dir: Path, embedding_model: str) -> None:
    model.save(
        str(output_dir / "model"),
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=embedding_model,
    )


def save_visualizations(model: Any, output_dir: Path, topic_count: int) -> list[str]:
    warnings: list[str] = []
    if topic_count == 0:
        return ["모든 문서가 이상치로 분류되어 시각화를 만들지 않았습니다."]

    try:
        model.visualize_barchart(top_n_topics=min(20, topic_count)).write_html(
            output_dir / "topic_barchart.html"
        )
    except Exception as exc:  # Optional output should not discard successful analysis.
        warnings.append(f"주제 막대그래프를 만들지 못했습니다: {exc}")

    if topic_count >= 2:
        try:
            model.visualize_topics().write_html(output_dir / "topic_map.html")
        except Exception as exc:  # Optional output should not discard successful analysis.
            warnings.append(f"주제 지도를 만들지 못했습니다: {exc}")
    return warnings


def write_outputs(
    model: Any,
    input_data: InputData,
    topics: Sequence[int],
    output_dir: Path,
    metadata: dict[str, object],
    should_save_model: bool,
    should_save_visualizations: bool,
) -> list[str]:
    documents, summaries = build_result_tables(model, input_data, topics)
    documents.to_csv(output_dir / "document_topics.csv", index=False, encoding="utf-8-sig")
    summaries.to_csv(output_dir / "topic_summary.csv", index=False, encoding="utf-8-sig")

    topic_count = len({int(topic) for topic in topics if int(topic) != -1})
    outlier_count = sum(int(topic) == -1 for topic in topics)
    output_names = ["document_topics.csv", "topic_summary.csv"]
    metadata.update(
        {
            "topic_count": topic_count,
            "outlier_count": outlier_count,
            "outputs": output_names,
        }
    )

    if should_save_model:
        save_model(model, output_dir, str(metadata["embedding_model"]))
        output_names.append("model/")

    warnings: list[str] = []
    if should_save_visualizations:
        warnings = save_visualizations(model, output_dir, topic_count)
        for name in ("topic_barchart.html", "topic_map.html"):
            if (output_dir / name).exists():
                output_names.append(name)

    metadata["warnings"] = warnings
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return warnings


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_columns:
            table = read_table(args.input, args.sheet)
            if table.attrs.get("source_sheet"):
                print(f"시트: {table.attrs['source_sheet']}")
            print("사용 가능한 열:")
            for column in table.columns:
                print(f"  - {column}")
            return 0

        if not args.text_columns:
            raise CLIError("분석할 열을 --text-columns로 지정하세요.")
        input_data = prepare_input(args.input, args.text_columns, args.sheet)
        min_topic_size = args.min_topic_size or choose_min_topic_size(len(input_data.documents))
        if min_topic_size < 2:
            raise CLIError("--min-topic-size는 2 이상이어야 합니다.")
        if min_topic_size > len(input_data.documents):
            raise CLIError("--min-topic-size가 문서 수보다 클 수 없습니다.")

        embedding_model = resolve_embedding_model(args.language, args.embedding_model)
        output_dir = args.output or default_output_dir(args.input)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"입력 파일: {args.input}")
        print(f"텍스트 열: {', '.join(input_data.text_columns)}")
        print(f"분석 문서: {len(input_data.documents)}개")
        if input_data.skipped_rows:
            print(f"빈 텍스트 제외: {input_data.skipped_rows}개 행")
        print(f"최소 주제 크기: {min_topic_size}")
        print("BERTopic 분석을 시작합니다...")

        model = create_topic_model(
            document_count=len(input_data.documents),
            language=args.language,
            embedding_model=embedding_model,
            min_topic_size=min_topic_size,
            reduce_topics=args.reduce_topics,
            random_seed=args.random_seed,
            verbose=not args.quiet,
        )
        topics, _ = model.fit_transform(input_data.documents)
        metadata: dict[str, object] = {
            "cli_version": __version__,
            "input": str(args.input.resolve()),
            "text_columns": input_data.text_columns,
            "sheet": input_data.sheet,
            "document_count": len(input_data.documents),
            "skipped_rows": input_data.skipped_rows,
            "language": args.language,
            "embedding_model": embedding_model,
            "min_topic_size": min_topic_size,
            "reduce_topics": args.reduce_topics,
            "random_seed": args.random_seed,
        }
        warnings = write_outputs(
            model=model,
            input_data=input_data,
            topics=topics,
            output_dir=output_dir,
            metadata=metadata,
            should_save_model=args.save_model,
            should_save_visualizations=args.visualizations,
        )

        topic_count = len({int(topic) for topic in topics if int(topic) != -1})
        outlier_count = sum(int(topic) == -1 for topic in topics)
        print(f"완료: 주제 {topic_count}개, 이상치 문서 {outlier_count}개")
        print(f"결과 폴더: {output_dir.resolve()}")
        for warning in warnings:
            print(f"주의: {warning}", file=sys.stderr)
        return 0
    except CLIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n사용자가 분석을 중단했습니다.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"분석 실패: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
