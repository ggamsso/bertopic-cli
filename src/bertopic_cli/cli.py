from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from zipfile import BadZipFile

from bertopic_cli import __version__


COHERENCE_METRICS = ("c_npmi", "u_mass")
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


def parse_positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("1 이상의 정수를 입력하세요.") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("1 이상의 정수를 입력하세요.")
    return number


def parse_topic_words(value: str) -> int:
    number = parse_positive_int(value)
    if number > 30:
        raise argparse.ArgumentTypeError("주제 키워드 수는 1~30 사이로 입력하세요.")
    return number


def parse_unit_interval(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("0 이상 1 이하의 숫자를 입력하세요.") from exc
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("0 이상 1 이하의 숫자를 입력하세요.")
    return number


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

    representation_group = parser.add_argument_group("주제 및 키워드 최적화")
    representation_group.add_argument(
        "--ngram-max",
        type=int,
        choices=(1, 2, 3),
        default=2,
        help="대표 키워드에 사용할 최대 단어 묶음 길이. 기본값: 2",
    )
    representation_group.add_argument(
        "--stopwords-file",
        type=Path,
        help="제외할 단어를 한 줄에 하나씩 적은 UTF-8 텍스트 파일",
    )
    representation_group.add_argument(
        "--min-word-frequency",
        type=parse_positive_int,
        default=1,
        metavar="N",
        help="BERTopic 단어 행렬에서 최소 빈도 N을 충족하지 못한 단어를 제외. 기본값: 1",
    )
    representation_group.add_argument(
        "--max-vocabulary",
        type=parse_positive_int,
        metavar="N",
        help="대표 키워드 후보를 빈도가 높은 최대 N개 단어로 제한",
    )
    representation_group.add_argument(
        "--reduce-frequent-words",
        action="store_true",
        help="여러 주제에서 반복되는 흔한 단어의 영향력을 낮춥니다.",
    )
    representation_group.add_argument(
        "--bm25-weighting",
        action="store_true",
        help="작은 데이터에서 흔한 단어에 더 강한 BM25 가중치를 사용합니다.",
    )
    representation_group.add_argument(
        "--representation",
        choices=("default", "keybert", "keybert-mmr"),
        default="default",
        help="대표 키워드 생성 방식. 기본값: default",
    )
    representation_group.add_argument(
        "--keyword-diversity",
        type=parse_unit_interval,
        default=0.3,
        metavar="숫자",
        help="keybert-mmr 키워드 다양성(0 이상 1 이하). 높을수록 중복이 줄어듭니다. 기본값: 0.3",
    )
    representation_group.add_argument(
        "--topic-words",
        type=parse_topic_words,
        default=10,
        metavar="N",
        help="주제마다 저장할 대표 키워드 수(1~30). 기본값: 10",
    )

    clustering_group = parser.add_argument_group("군집 및 이상치 최적화")
    clustering_group.add_argument(
        "--umap-neighbors",
        type=parse_positive_int,
        metavar="N",
        help="UMAP 이웃 수. 작으면 세밀하게, 크면 넓게 묶습니다. 기본값: 최대 15 자동",
    )
    clustering_group.add_argument(
        "--min-samples",
        type=parse_positive_int,
        metavar="N",
        help="HDBSCAN의 보수성. 낮추면 이상치가 감소합니다. 기본값: 최소 주제 크기",
    )
    clustering_group.add_argument(
        "--outlier-strategy",
        choices=("none", "c-tf-idf", "embeddings", "distributions"),
        default="none",
        help="-1 이상치 문서를 주제에 다시 배정하는 방식. 기본값: none",
    )
    clustering_group.add_argument(
        "--outlier-threshold",
        type=parse_unit_interval,
        default=0.1,
        metavar="숫자",
        help="이상치 재배정에 필요한 최소 유사도(0 이상 1 이하). 기본값: 0.1",
    )
    clustering_group.add_argument(
        "--low-memory",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="메모리를 절약합니다. 속도를 우선하면 --no-low-memory를 사용합니다. 기본값: 사용",
    )
    clustering_group.add_argument(
        "--calculate-probabilities",
        action="store_true",
        help="문서별 주제 확률을 계산하고 결과에 저장합니다. 실행 시간과 메모리가 증가합니다.",
    )

    zeroshot_group = parser.add_argument_group("미리 아는 주제 지정(zero-shot)")
    zeroshot_group.add_argument(
        "--zeroshot-topics",
        nargs="+",
        metavar="주제",
        help="미리 아는 주제 이름들. 각 이름을 따옴표로 묶으세요. 나머지 문서만 군집합니다.",
    )
    zeroshot_group.add_argument(
        "--zeroshot-topics-file",
        type=Path,
        help="주제 이름을 한 줄에 하나씩 적은 UTF-8 텍스트 파일. --zeroshot-topics 대신 사용합니다.",
    )
    zeroshot_group.add_argument(
        "--zeroshot-min-similarity",
        type=parse_unit_interval,
        default=0.7,
        metavar="숫자",
        help=(
            "주제 이름에 배정할 최소 유사도(0 이상 1 이하). 기본값: 0.7. "
            "초록처럼 긴 문서는 0.7에서 거의 배정되지 않아 0.4~0.55로 낮춰야 할 수 있습니다."
        ),
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
        "--coherence",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "주제 품질 지표(coherence, 키워드 다양성) 계산 여부. 기본값: 계산. "
            "문서 6천 건 기준 약 5초가 추가로 걸립니다."
        ),
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


def load_stop_words(path: Path | None) -> list[str]:
    if path is None:
        return []
    if not path.exists():
        raise CLIError(f"불용어 파일을 찾을 수 없습니다: {path}")
    if not path.is_file():
        raise CLIError(f"불용어 경로가 파일이 아닙니다: {path}")
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CLIError(f"불용어 파일을 읽지 못했습니다: {exc}") from exc

    words = list(
        dict.fromkeys(
            line.strip().casefold()
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        )
    )
    if not words:
        raise CLIError("불용어 파일에 사용할 단어가 없습니다.")
    spaced_words = [word for word in words if any(character.isspace() for character in word)]
    if spaced_words:
        examples = ", ".join(spaced_words[:3])
        raise CLIError(
            "불용어 파일에는 한 줄에 공백 없는 한 단어만 입력하세요. "
            f"확인할 항목: {examples}"
        )
    return words


def load_zeroshot_topics(path: Path | None) -> list[str]:
    if path is None:
        return []
    if not path.exists():
        raise CLIError(f"zero-shot 주제 파일을 찾을 수 없습니다: {path}")
    if not path.is_file():
        raise CLIError(f"zero-shot 주제 경로가 파일이 아닙니다: {path}")
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CLIError(f"zero-shot 주제 파일을 읽지 못했습니다: {exc}") from exc

    labels = list(
        dict.fromkeys(
            line.strip()
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        )
    )
    if not labels:
        raise CLIError("zero-shot 주제 파일에 사용할 주제가 없습니다.")
    return labels


def resolve_zeroshot_topics(inline: Sequence[str] | None, path: Path | None) -> list[str]:
    if inline and path:
        raise CLIError("--zeroshot-topics와 --zeroshot-topics-file은 함께 쓸 수 없습니다.")
    if path:
        return load_zeroshot_topics(path)
    if not inline:
        return []
    labels = list(dict.fromkeys(label.strip() for label in inline if label.strip()))
    if not labels:
        raise CLIError("--zeroshot-topics에 사용할 주제가 없습니다.")
    return labels


def create_representation_model(
    name: str,
    topic_words: int,
    keyword_diversity: float,
    random_seed: int,
) -> Any:
    if name == "default":
        return None

    from bertopic.representation import KeyBERTInspired, MaximalMarginalRelevance

    keybert = KeyBERTInspired(top_n_words=topic_words, random_state=random_seed)
    if name == "keybert":
        return keybert
    return [
        keybert,
        MaximalMarginalRelevance(diversity=keyword_diversity, top_n_words=topic_words),
    ]


def create_topic_model(
    document_count: int,
    language: str,
    embedding_model: str,
    min_topic_size: int,
    reduce_topics: int | str | None,
    random_seed: int,
    verbose: bool,
    *,
    ngram_max: int = 2,
    custom_stop_words: Sequence[str] = (),
    min_word_frequency: int = 1,
    max_vocabulary: int | None = None,
    reduce_frequent_words: bool = False,
    bm25_weighting: bool = False,
    representation: str = "default",
    keyword_diversity: float = 0.3,
    topic_words: int = 10,
    umap_neighbors: int | None = None,
    min_samples: int | None = None,
    low_memory: bool = True,
    calculate_probabilities: bool = False,
    zeroshot_topics: Sequence[str] = (),
    zeroshot_min_similarity: float = 0.7,
) -> Any:
    from bertopic import BERTopic
    from bertopic.vectorizers import ClassTfidfTransformer
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from umap import UMAP

    n_neighbors = (
        umap_neighbors if umap_neighbors is not None else max(2, min(15, document_count - 1))
    )
    n_components = min(5, max(2, document_count // 3))
    if custom_stop_words:
        stop_words = set(custom_stop_words)
        if language == "english":
            stop_words.update(ENGLISH_STOP_WORDS)
        resolved_stop_words: str | list[str] | None = sorted(stop_words)
    else:
        resolved_stop_words = "english" if language == "english" else None

    representation_model = create_representation_model(
        representation,
        topic_words,
        keyword_diversity,
        random_seed,
    )

    return BERTopic(
        embedding_model=embedding_model,
        umap_model=UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            min_dist=0.0,
            metric="cosine",
            random_state=random_seed,
            low_memory=low_memory,
        ),
        hdbscan_model=HDBSCAN(
            min_cluster_size=min_topic_size,
            min_samples=min_samples if min_samples is not None else min_topic_size,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        ),
        vectorizer_model=CountVectorizer(
            stop_words=resolved_stop_words,
            ngram_range=(1, ngram_max),
            min_df=min_word_frequency,
            max_features=max_vocabulary,
        ),
        ctfidf_model=ClassTfidfTransformer(
            bm25_weighting=bm25_weighting,
            reduce_frequent_words=reduce_frequent_words,
        ),
        representation_model=representation_model,
        zeroshot_topic_list=list(zeroshot_topics) or None,
        zeroshot_min_similarity=zeroshot_min_similarity,
        top_n_words=topic_words,
        min_topic_size=min_topic_size,
        nr_topics=reduce_topics,
        low_memory=low_memory,
        calculate_probabilities=calculate_probabilities,
        verbose=verbose,
    )


def matched_zeroshot_topics(model: Any, zeroshot_topics: Sequence[str]) -> dict[int, str]:
    """Map final topic id -> zero-shot name, for the names that actually matched.

    BERTopic drops zero-shot names that no document reached, and renumbers the
    rest from 0, so the requested list cannot be used as the mapping directly.
    """
    mapping = getattr(model, "_topic_id_to_zeroshot_topic_idx", None) or {}
    return {
        int(topic_id): zeroshot_topics[index]
        for topic_id, index in mapping.items()
        if 0 <= index < len(zeroshot_topics)
    }


def reduce_outlier_topics(
    model: Any,
    documents: Sequence[str],
    topics: Sequence[int],
    strategy: str,
    threshold: float,
) -> list[int]:
    resolved_topics = [int(topic) for topic in topics]
    if strategy == "none" or -1 not in resolved_topics:
        return resolved_topics
    if not any(topic != -1 for topic in resolved_topics):
        return resolved_topics

    updated_topics = model.reduce_outliers(
        list(documents),
        resolved_topics,
        strategy=strategy,
        threshold=threshold,
    )
    updated_topics = [int(topic) for topic in updated_topics]
    model.update_topics(
        list(documents),
        topics=updated_topics,
        top_n_words=model.top_n_words,
        vectorizer_model=model.vectorizer_model,
        ctfidf_model=model.ctfidf_model,
        representation_model=model.representation_model,
    )
    return updated_topics


def assigned_topic_probabilities(
    probabilities: Any,
    probability_topics: Sequence[int],
    final_topics: Sequence[int],
) -> list[float | None] | None:
    if probabilities is None:
        return None

    import numpy as np

    values = np.asarray(probabilities)
    if values.ndim not in {1, 2} or len(values) != len(final_topics):
        return None

    resolved: list[float | None] = []
    for index, (probability_topic, final_topic) in enumerate(zip(probability_topics, final_topics)):
        probability_topic = int(probability_topic)
        final_topic = int(final_topic)
        if probability_topic != final_topic or final_topic == -1:
            resolved.append(None)
        elif values.ndim == 1:
            resolved.append(float(values[index]))
        elif final_topic < values.shape[1]:
            resolved.append(float(values[index, final_topic]))
        else:
            resolved.append(None)
    return resolved


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


def compute_coherence_metrics(
    model: Any,
    documents: Sequence[str],
    topic_words: int = 10,
) -> dict[str, object]:
    """주제 품질 지표를 계산한다: coherence 3종과 키워드 다양성.

    coherence는 유니그램만으로 계산한다. scikit-learn의 analyzer는 토큰을
    [유니그램 전부, 바이그램 전부] 순서로 이어붙이기 때문에, 좁은 윈도우를
    쓰는 c_npmi에서 "music"과 "music therapy" 같은 쌍이 실제보다 훨씬
    멀리 떨어진 것으로 계산된다. 다양성은 윈도우와 무관하므로 사용자에게
    보여주는 키워드 전체(바이그램 포함)로 센다.
    """
    from gensim.corpora import Dictionary
    from gensim.models.coherencemodel import CoherenceModel

    representations = {
        int(topic): [word for word, _ in words if word][:topic_words]
        for topic, words in model.get_topics().items()
        if int(topic) != -1
    }
    representations = {topic: words for topic, words in representations.items() if words}
    if not representations:
        raise CLIError("이상치를 제외한 주제가 없어 품질 지표를 계산할 수 없습니다.")

    analyzer = model.vectorizer_model.build_analyzer()
    tokenized = [[word for word in analyzer(document) if " " not in word] for document in documents]
    dictionary = Dictionary(tokenized)
    corpus = [dictionary.doc2bow(tokens) for tokens in tokenized]

    scored_topics = [
        unigrams
        for words in representations.values()
        if len(unigrams := [word for word in words if word in dictionary.token2id]) >= 2
    ]
    if not scored_topics:
        raise CLIError("주제 키워드가 문서 어휘와 겹치지 않아 coherence를 계산할 수 없습니다.")

    metrics: dict[str, object] = {"topics_scored": len(scored_topics)}
    for metric in COHERENCE_METRICS:
        score = float(
            CoherenceModel(
                topics=scored_topics,
                texts=tokenized,
                corpus=corpus,
                dictionary=dictionary,
                coherence=metric,
                processes=1,
            ).get_coherence()
        )
        metrics[metric] = round(score, 4) if math.isfinite(score) else None

    keywords = [word for words in representations.values() for word in words]
    metrics["diversity"] = round(len(set(keywords)) / len(keywords), 4)
    return metrics


def format_coherence_metrics(metrics: dict[str, object]) -> str:
    def label(value: object) -> str:
        return f"{value:.4f}" if isinstance(value, (int, float)) else "측정불가"

    return (
        f"품질 지표: c_npmi {label(metrics.get('c_npmi'))} / "
        f"u_mass {label(metrics.get('u_mass'))} / "
        f"diversity {label(metrics.get('diversity'))} "
        f"(주제 {metrics.get('topics_scored')}개 기준)"
    )


def build_result_tables(
    model: Any,
    input_data: InputData,
    topics: Sequence[int],
    topic_words: int,
    probabilities: Any = None,
    probability_topics: Sequence[int] | None = None,
) -> tuple[Any, Any]:
    import pandas as pd

    unique_topics = sorted(set(int(topic) for topic in topics))
    labels = {topic: topic_label(model, topic) for topic in unique_topics}
    keywords = {topic: topic_keywords(model, topic, topic_words) for topic in unique_topics}

    documents = input_data.table.copy()
    documents["topic"] = [int(topic) for topic in topics]
    documents["topic_label"] = documents["topic"].map(labels)
    documents["topic_keywords"] = documents["topic"].map(keywords)
    if probabilities is not None and probability_topics is not None:
        topic_probabilities = assigned_topic_probabilities(
            probabilities,
            probability_topics,
            topics,
        )
        if topic_probabilities is not None:
            documents["topic_probability"] = topic_probabilities

    topic_info = model.get_topic_info()
    summaries: list[dict[str, object]] = []
    for row in topic_info.itertuples(index=False):
        topic = int(getattr(row, "Topic"))
        summaries.append(
            {
                "topic": topic,
                "document_count": int(getattr(row, "Count")),
                "topic_label": labels.get(topic, topic_label(model, topic)),
                "topic_keywords": keywords.get(topic, topic_keywords(model, topic, topic_words)),
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
    topic_words: int = 10,
    probabilities: Any = None,
    probability_topics: Sequence[int] | None = None,
    extra_warnings: Sequence[str] = (),
) -> list[str]:
    documents, summaries = build_result_tables(
        model,
        input_data,
        topics,
        topic_words,
        probabilities,
        probability_topics,
    )
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

    warnings: list[str] = list(extra_warnings)
    if should_save_visualizations:
        warnings.extend(save_visualizations(model, output_dir, topic_count))
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
        document_count = len(input_data.documents)
        min_topic_size = (
            args.min_topic_size
            if args.min_topic_size is not None
            else choose_min_topic_size(document_count)
        )
        if min_topic_size < 2:
            raise CLIError("--min-topic-size는 2 이상이어야 합니다.")
        if min_topic_size > document_count:
            raise CLIError("--min-topic-size가 문서 수보다 클 수 없습니다.")
        if args.min_word_frequency > document_count:
            raise CLIError("--min-word-frequency가 문서 수보다 클 수 없습니다.")

        umap_neighbors = (
            args.umap_neighbors
            if args.umap_neighbors is not None
            else max(2, min(15, document_count - 1))
        )
        if umap_neighbors < 2:
            raise CLIError("--umap-neighbors는 2 이상이어야 합니다.")
        if umap_neighbors >= document_count:
            raise CLIError("--umap-neighbors는 문서 수보다 작아야 합니다.")

        min_samples = args.min_samples if args.min_samples is not None else min_topic_size
        if min_samples > document_count:
            raise CLIError("--min-samples가 문서 수보다 클 수 없습니다.")

        embedding_model = resolve_embedding_model(args.language, args.embedding_model)
        custom_stop_words = load_stop_words(args.stopwords_file)
        zeroshot_topics = resolve_zeroshot_topics(
            args.zeroshot_topics, args.zeroshot_topics_file
        )
        if zeroshot_topics and isinstance(args.reduce_topics, int):
            if args.reduce_topics <= len(zeroshot_topics):
                raise CLIError(
                    f"--reduce-topics({args.reduce_topics})는 zero-shot 주제 수"
                    f"({len(zeroshot_topics)})보다 커야 합니다."
                )
        output_dir = args.output or default_output_dir(args.input)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"입력 파일: {args.input}")
        print(f"텍스트 열: {', '.join(input_data.text_columns)}")
        print(f"분석 문서: {document_count}개")
        if input_data.skipped_rows:
            print(f"빈 텍스트 제외: {input_data.skipped_rows}개 행")
        print(f"최소 주제 크기: {min_topic_size}")
        print(f"UMAP 이웃 수: {umap_neighbors}, HDBSCAN min_samples: {min_samples}")
        if custom_stop_words:
            print(f"사용자 불용어: {len(custom_stop_words)}개")
        if zeroshot_topics:
            print(
                f"zero-shot 주제: {len(zeroshot_topics)}개 "
                f"(최소 유사도 {args.zeroshot_min_similarity})"
            )
        print("BERTopic 분석을 시작합니다...")

        model = create_topic_model(
            document_count=document_count,
            language=args.language,
            embedding_model=embedding_model,
            min_topic_size=min_topic_size,
            reduce_topics=args.reduce_topics,
            random_seed=args.random_seed,
            verbose=not args.quiet,
            ngram_max=args.ngram_max,
            custom_stop_words=custom_stop_words,
            min_word_frequency=args.min_word_frequency,
            max_vocabulary=args.max_vocabulary,
            reduce_frequent_words=args.reduce_frequent_words,
            bm25_weighting=args.bm25_weighting,
            representation=args.representation,
            keyword_diversity=args.keyword_diversity,
            topic_words=args.topic_words,
            umap_neighbors=umap_neighbors,
            min_samples=min_samples,
            low_memory=args.low_memory,
            calculate_probabilities=args.calculate_probabilities,
            zeroshot_topics=zeroshot_topics,
            zeroshot_min_similarity=args.zeroshot_min_similarity,
        )
        topics, probabilities = model.fit_transform(input_data.documents)
        probability_topics = [int(topic) for topic in topics]
        outlier_count_before = sum(topic == -1 for topic in probability_topics)

        matched_zeroshot = matched_zeroshot_topics(model, zeroshot_topics)
        zeroshot_document_count = sum(
            topic in matched_zeroshot for topic in probability_topics
        )
        if zeroshot_topics:
            unmatched = [
                label for label in zeroshot_topics if label not in matched_zeroshot.values()
            ]
            print(
                f"zero-shot 배정: {zeroshot_document_count}개 문서, "
                f"주제 {len(matched_zeroshot)}/{len(zeroshot_topics)}개 사용"
            )
            if unmatched:
                print(
                    f"주의: 문서를 받지 못해 제외된 zero-shot 주제 {len(unmatched)}개: "
                    f"{', '.join(unmatched[:3])}"
                    + (" 외" if len(unmatched) > 3 else ""),
                    file=sys.stderr,
                )
            if not matched_zeroshot:
                print(
                    "주의: 최소 유사도를 넘은 문서가 없어 일반 군집만 수행했습니다. "
                    "--zeroshot-min-similarity를 낮춰보세요.",
                    file=sys.stderr,
                )
        topics = reduce_outlier_topics(
            model,
            input_data.documents,
            probability_topics,
            args.outlier_strategy,
            args.outlier_threshold,
        )
        outlier_count_after = sum(topic == -1 for topic in topics)
        reassigned_outliers = outlier_count_before - outlier_count_after
        if args.outlier_strategy != "none":
            if outlier_count_before == document_count:
                print("이상치를 배정할 기존 주제가 없어 -1 문서를 그대로 유지합니다.")
            else:
                print(f"이상치 재배정: {reassigned_outliers}개 문서")

        coherence_metrics: dict[str, object] | None = None
        coherence_warnings: list[str] = []
        if args.coherence:
            try:
                coherence_metrics = compute_coherence_metrics(
                    model,
                    input_data.documents,
                    args.topic_words,
                )
            except ImportError:
                coherence_warnings.append(
                    "gensim이 설치되지 않아 품질 지표를 건너뜁니다. uv sync로 의존성을 갱신하세요."
                )
            except Exception as exc:  # 지표 계산 실패로 분석 결과를 버리지 않는다
                coherence_warnings.append(f"품질 지표를 계산하지 못했습니다: {exc}")

        metadata: dict[str, object] = {
            "cli_version": __version__,
            "input": str(args.input.resolve()),
            "text_columns": input_data.text_columns,
            "sheet": input_data.sheet,
            "document_count": document_count,
            "skipped_rows": input_data.skipped_rows,
            "language": args.language,
            "embedding_model": embedding_model,
            "min_topic_size": min_topic_size,
            "reduce_topics": args.reduce_topics,
            "ngram_max": args.ngram_max,
            "stopwords_file": str(args.stopwords_file.resolve()) if args.stopwords_file else None,
            "custom_stopword_count": len(custom_stop_words),
            "min_word_frequency": args.min_word_frequency,
            "max_vocabulary": args.max_vocabulary,
            "reduce_frequent_words": args.reduce_frequent_words,
            "bm25_weighting": args.bm25_weighting,
            "representation": args.representation,
            "keyword_diversity": args.keyword_diversity,
            "topic_words": args.topic_words,
            "umap_neighbors": umap_neighbors,
            "min_samples": min_samples,
            "outlier_strategy": args.outlier_strategy,
            "outlier_threshold": args.outlier_threshold,
            "outlier_count_before_reduction": outlier_count_before,
            "outlier_documents_reassigned": reassigned_outliers,
            "zeroshot_topics": zeroshot_topics,
            "zeroshot_min_similarity": args.zeroshot_min_similarity if zeroshot_topics else None,
            "zeroshot_topics_matched": [
                matched_zeroshot[topic] for topic in sorted(matched_zeroshot)
            ],
            "zeroshot_document_count": zeroshot_document_count,
            "low_memory": args.low_memory,
            "calculate_probabilities": args.calculate_probabilities,
            "random_seed": args.random_seed,
            "coherence": coherence_metrics,
        }
        warnings = write_outputs(
            model=model,
            input_data=input_data,
            topics=topics,
            output_dir=output_dir,
            metadata=metadata,
            should_save_model=args.save_model,
            should_save_visualizations=args.visualizations,
            topic_words=args.topic_words,
            probabilities=probabilities if args.calculate_probabilities else None,
            probability_topics=probability_topics if args.calculate_probabilities else None,
            extra_warnings=coherence_warnings,
        )

        topic_count = len({int(topic) for topic in topics if int(topic) != -1})
        outlier_count = sum(int(topic) == -1 for topic in topics)
        print(f"완료: 주제 {topic_count}개, 이상치 문서 {outlier_count}개")
        if coherence_metrics is not None:
            print(format_coherence_metrics(coherence_metrics))
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
