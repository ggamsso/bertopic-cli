# BERTopic CLI

Python 코드를 작성하지 않고 CSV, TSV 또는 XLSX 문서를 BERTopic으로 분석하는 명령줄 도구입니다.

## Windows 10/11 실습 준비

이 절은 개발 도구가 전혀 설치되지 않은 Windows PC를 기준으로 합니다. 모든 명령은 **PowerShell**에서 실행합니다.

### 1. PowerShell 열기

시작 메뉴에서 `PowerShell`을 검색해 **Windows PowerShell**을 실행합니다. 관리자 권한은 일반적으로 필요하지 않습니다.

### 2. Git 설치

PowerShell에 다음 명령을 붙여넣고 Enter를 누릅니다.

```powershell
winget install --id Git.Git -e --source winget
```

설치가 끝나면 PowerShell 창을 완전히 닫고 새로 엽니다. 다음 명령에서 버전이 표시되면 설치가 완료된 것입니다.

```powershell
git --version
```

`winget` 명령을 사용할 수 없다면 [Git for Windows 공식 설치 페이지](https://git-scm.com/install/windows)에서 x64 설치 파일을 내려받아 기본 설정으로 설치합니다.

### 3. 실습 프로젝트 내려받기

문서 폴더로 이동한 뒤 프로젝트 저장소를 내려받습니다.

```powershell
cd "$HOME\Documents"
git clone https://github.com/ggamsso/bertopic-cli.git
cd ".\bertopic-cli"
```

이미 `bertopic-cli` 프로젝트 폴더를 전달받았다면 `git clone`은 생략하고 해당 폴더로 이동합니다.

```powershell
cd "C:\실제\bertopic-cli\폴더\경로"
```

현재 위치가 프로젝트 폴더인지 확인합니다. 목록에 `README.md`, `pyproject.toml`, `uv.lock`이 보여야 합니다.

```powershell
Get-ChildItem
```

### 4. uv 설치

`uv`가 Python 3.12와 필요한 패키지를 자동으로 설치하므로 Python을 별도로 설치하지 않아도 됩니다.

```powershell
winget install --id=astral-sh.uv -e
```

설치가 끝나면 PowerShell을 닫았다가 다시 열고 프로젝트 폴더로 돌아옵니다.

```powershell
cd "$HOME\Documents\bertopic-cli"
uv --version
```

`winget`을 사용할 수 없다면 다음 공식 설치 명령을 사용합니다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 5. Python과 분석 환경 설치

프로젝트 폴더에서 다음 두 명령을 순서대로 실행합니다.

```powershell
uv python install 3.12
uv sync --locked
```

처음 설치할 때는 Python과 여러 분석 패키지를 내려받으므로 시간이 걸릴 수 있습니다. 설치 중에는 PowerShell을 닫지 마세요.

설치가 끝나면 명령줄 도구가 실행되는지 확인합니다.

```powershell
uv run bertopic-cli --help
```

### 6. Excel 파일 준비

분석할 Excel 파일을 프로젝트의 `data` 폴더에 복사합니다. 예를 들어 파일 이름을 `papers.xlsx`로 정하면 경로는 다음과 같습니다.

```text
bertopic-cli\data\papers.xlsx
```

한 행에는 논문 하나가 있어야 하며, 첫 행에는 열 이름이 있어야 합니다. 예시는 다음과 같습니다.

| 년도 | 제목 | 초록 | 수록정보 | DOI |
|---:|---|---|---|---|
| 2025 | 논문 제목 | 논문 초록 | 저널 수록정보 | 10.xxxx/example |

BERTopic 분석에는 `제목`과 `초록` 열을 사용합니다. 일부 초록이 비어 있어도 제목이 있으면 분석할 수 있습니다.

먼저 Excel의 시트 이름과 열 이름이 맞는지 확인합니다.

```powershell
uv run bertopic-cli ".\data\papers.xlsx" --sheet "전체 논문" --list-columns
```

### 7. BERTopic 실행

영어 초록이 포함된 논문을 제목과 초록으로 분석하는 실습 명령입니다.

```powershell
uv run bertopic-cli ".\data\papers.xlsx" `
  --sheet "전체 논문" `
  --text-columns "제목" "초록" `
  --language english `
  --min-topic-size 5 `
  --output ".\outputs\practice_results"
```

PowerShell에서 각 줄 끝의 백틱 기호는 다음 줄에 명령이 이어진다는 뜻입니다. 한 줄로 입력해도 됩니다.

첫 분석에서는 임베딩 모델을 추가로 내려받으므로 인터넷 연결이 필요합니다. 완료되면 `outputs\practice_results` 폴더가 만들어집니다.

### 8. 결과 확인

결과 폴더에는 논문별 주제, 주제 요약, 그래프와 학습 모델이 저장됩니다.

```powershell
Get-ChildItem ".\outputs\practice_results"
Start-Process ".\outputs\practice_results\topic_barchart.html"
Start-Process ".\outputs\practice_results\topic_map.html"
```

### 9. 다음 실습에서 프로젝트 업데이트

프로젝트 폴더에서 다음 명령을 실행하면 변경된 코드와 패키지 정보를 반영할 수 있습니다.

```powershell
git pull
uv sync --locked
```

### 자주 발생하는 설치 문제

- `git`을 찾을 수 없다고 표시됨: PowerShell을 모두 닫고 새로 연 뒤 `git --version`을 다시 실행합니다.
- `uv`를 찾을 수 없다고 표시됨: PowerShell을 새로 열고 `uv --version`을 다시 실행합니다.
- 파일을 찾을 수 없다고 표시됨: Excel 파일이 실제로 `data` 폴더에 있는지 확인하고 경로 전체를 따옴표로 감쌉니다.
- 회사나 기관 네트워크에서 다운로드가 차단됨: 방화벽 또는 프록시 담당자에게 GitHub, PyPI, Hugging Face 접속 허용 여부를 확인합니다.
- 주제 번호 `-1` 또는 `Outlier`가 보임: 어느 주제에도 안정적으로 속하지 않은 문서이며 오류가 아닙니다.

### 공식 설치 문서

- [Git for Windows](https://git-scm.com/install/windows)
- [uv 설치](https://docs.astral.sh/uv/getting-started/installation/)
- [uv Python 설치](https://docs.astral.sh/uv/guides/install-python/)
- [uv 프로젝트 동기화](https://docs.astral.sh/uv/concepts/projects/sync/)

## 기본 사용법

```powershell
uv run bertopic-cli documents.csv --text-columns text
```

결과는 입력 파일 옆의 `documents_bertopic_results` 폴더에 저장됩니다.

텍스트 열 이름이 `본문`이라면 다음과 같이 실행합니다.

```powershell
uv run bertopic-cli documents.csv --text-columns 본문
```

제목과 본문을 함께 분석하려면 컬럼 이름을 원하는 결합 순서대로 나열합니다.

```powershell
uv run bertopic-cli documents.csv --text-columns title abstract
```

각 행의 `title`과 `abstract`를 줄바꿈으로 연결해 하나의 문서로 사용합니다. 일부 값이 비어 있으면 존재하는 값만 사용하며, 지정한 컬럼이 모두 비어 있는 행은 분석에서 제외합니다.

영어 문서만 분석한다면 영어 모델과 불용어 설정을 사용합니다.

```powershell
uv run bertopic-cli documents.csv --text-columns text --language english
```

Excel 파일도 같은 방법으로 실행할 수 있습니다. 생략하면 첫 번째 시트를 읽습니다.

```powershell
uv run bertopic-cli documents.xlsx --text-columns text
```

여러 시트 중 하나를 선택하려면 시트 이름을 지정합니다.

```powershell
uv run bertopic-cli documents.xlsx --sheet 설문응답 --text-columns title text
```

## 결과 파일

- `document_topics.csv`: 원본 문서별 주제 번호, 주제 이름, 대표 단어. `--calculate-probabilities`를 사용하면 `topic_probability` 열도 추가됩니다.
- `topic_summary.csv`: 주제별 문서 수와 대표 단어
- `topic_barchart.html`: 주제별 대표 단어 그래프
- `topic_map.html`: 주제 사이의 관계를 보여주는 지도
- `model/`: 나중에 재사용할 BERTopic 모델
- `run_metadata.json`: 입력 파일, 실제 적용된 최적화 설정, 이상치 재배정 수 기록

CSV 결과는 UTF-8 BOM 형식으로 저장하므로 Excel에서 한글이 깨지지 않습니다.

## 처음 사용할 때 권장하는 설정

먼저 별도 최적화 옵션 없이 실행해 결과를 확인합니다.

```powershell
uv run bertopic-cli ".\data\papers.xlsx" `
  --text-columns "제목" "초록" `
  --language multilingual
```

대표 키워드에 `연구`, `결과`, `분석`처럼 의미가 약한 단어가 반복될 때는 키워드 정리 옵션을 추가합니다.

```powershell
uv run bertopic-cli ".\data\papers.xlsx" `
  --text-columns "제목" "초록" `
  --language multilingual `
  --min-word-frequency 2 `
  --reduce-frequent-words `
  --representation keybert
```

이 옵션들은 대표 키워드를 읽기 좋게 만들지만 문서가 어느 주제에 배정되는지는 직접 바꾸지 않습니다.

## 불용어 파일 사용

한국어에는 CLI가 자동 적용할 수 있는 공통 불용어 목록이 없습니다. 분석 목적에 맞는 단어를 한 줄에 하나씩 적은 UTF-8 텍스트 파일을 준비합니다. 불용어 하나에는 공백을 넣지 않습니다.

```text
# 설명 줄은 #으로 시작합니다.
연구
결과
분석
통해
대한
```

예를 들어 위 내용을 `data\stopwords-ko.txt`로 저장했다면 다음처럼 사용합니다.

```powershell
uv run bertopic-cli ".\data\papers.xlsx" `
  --text-columns "제목" "초록" `
  --stopwords-file ".\data\stopwords-ko.txt" `
  --reduce-frequent-words
```

불용어는 임베딩을 만들기 전 원문에서 삭제되지 않고, 토픽의 대표 키워드를 계산할 때만 제외됩니다. 따라서 문장의 의미 정보는 유지됩니다. `--language english`와 불용어 파일을 함께 사용하면 기본 영어 불용어와 파일의 단어를 모두 제외합니다.

## 옵션 설명

`공식 문서` 열의 링크는 각 CLI 옵션이 내부적으로 연결하는 BERTopic, UMAP, HDBSCAN 설정의 설명으로 이동합니다. 파일 읽기와 결과 저장처럼 이 프로젝트에서 직접 구현한 기능은 `CLI 자체 기능`으로 표시합니다.

### 기본 옵션

| 옵션 | 설명 | 기본값 | 공식 문서 |
|---|---|---|---|
| `input` | 분석할 CSV, TSV 또는 XLSX 파일입니다. | 필수 | CLI 자체 기능 |
| `--text-columns 열1 열2 ...` | 분석할 열을 순서대로 합칩니다. 분석 실행 시 필수입니다. | 없음 | CLI 자체 기능 |
| `--sheet 이름` | XLSX에서 읽을 시트를 선택합니다. | 첫 번째 시트 | CLI 자체 기능 |
| `--language {multilingual, english}` | 한국어·혼합 언어 또는 영어 임베딩 모델을 선택합니다. | `multilingual` | [language](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#language) |
| `--embedding-model 이름` | 사용할 SentenceTransformers 모델을 직접 지정합니다. | 언어별 자동 선택 | [Embeddings](https://maartengr.github.io/BERTopic/getting_started/embeddings/embeddings.html) |
| `--min-topic-size N` | 주제 하나를 만들 최소 문서 수입니다. | 문서 수에 따라 자동 | [min_topic_size](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#min_topic_size) |
| `--reduce-topics {none, auto, N}` | 생성된 주제를 나중에 합칩니다. | `none` | [Topic Reduction](https://maartengr.github.io/BERTopic/getting_started/topicreduction/topicreduction.html) |
| `--random-seed N` | 반복 실행 결과를 재현하기 위한 난수값입니다. | `42` | [Preventing Stochastic Behavior](https://maartengr.github.io/BERTopic/getting_started/best_practices/best_practices.html#preventing-stochastic-behavior) |
| `--output 폴더` | 결과를 저장할 폴더입니다. | 입력 파일 옆 자동 생성 | CLI 자체 기능 |
| `--save-model`, `--no-save-model` | 학습 모델 저장 여부를 선택합니다. | 저장 | [Serialization](https://maartengr.github.io/BERTopic/getting_started/serialization/serialization.html) |
| `--visualizations`, `--no-visualizations` | HTML 시각화 저장 여부를 선택합니다. | 저장 | [Visualization](https://maartengr.github.io/BERTopic/getting_started/visualization/visualization.html) |
| `--list-columns` | 입력 파일의 열 이름만 출력합니다. | 사용 안 함 | CLI 자체 기능 |
| `--quiet` | BERTopic 진행 로그를 줄입니다. | 사용 안 함 | CLI 자체 기능 |
| `--version` | CLI 버전을 출력합니다. | 해당 없음 | CLI 자체 기능 |

### 대표 키워드 최적화

| 옵션 | 언제 사용하는가 | 기본값 | 공식 문서 |
|---|---|---|---|
| `--ngram-max {1, 2, 3}` | `인공지능 교육`처럼 여러 단어로 된 표현을 찾습니다. | `2` | [ngram_range](https://maartengr.github.io/BERTopic/getting_started/vectorizers/vectorizers.html#ngram_range) |
| `--stopwords-file 파일` | 조사, 상투어, 도메인 공통어를 대표 키워드에서 제외합니다. | 없음 | [stop_words](https://maartengr.github.io/BERTopic/getting_started/vectorizers/vectorizers.html#stop_words) |
| `--min-word-frequency N` | BERTopic 단어 행렬에서 최소 빈도 N을 충족하지 못한 희귀 단어를 제외합니다. | `1` | [min_df](https://maartengr.github.io/BERTopic/getting_started/vectorizers/vectorizers.html#min_df) |
| `--max-vocabulary N` | 대규모 데이터의 키워드 후보 수와 메모리 사용량을 제한합니다. | 제한 없음 | [max_features](https://maartengr.github.io/BERTopic/getting_started/vectorizers/vectorizers.html#max_features) |
| `--reduce-frequent-words` | 여러 주제에서 반복되는 흔한 단어의 영향력을 낮춥니다. | 사용 안 함 | [reduce_frequent_words](https://maartengr.github.io/BERTopic/getting_started/ctfidf/ctfidf.html#reduce_frequent_words) |
| `--bm25-weighting` | 작은 데이터에서 흔한 단어가 대표어가 되는 현상을 줄입니다. | 사용 안 함 | [bm25_weighting](https://maartengr.github.io/BERTopic/getting_started/ctfidf/ctfidf.html#bm25_weighting) |
| `--representation {default, keybert, keybert-mmr}` | 의미 기반으로 대표 키워드를 다듬습니다. | `default` | [KeyBERTInspired](https://maartengr.github.io/BERTopic/getting_started/representation/representation.html#keybertinspired) |
| `--keyword-diversity 숫자` | `keybert-mmr`에서 비슷한 키워드의 중복을 줄입니다. 0 이상 1 이하로 입력합니다. | `0.3` | [MaximalMarginalRelevance](https://maartengr.github.io/BERTopic/getting_started/representation/representation.html#maximalmarginalrelevance) |
| `--topic-words N` | 주제마다 CSV에 저장할 대표 키워드 수를 정합니다. | `10` | [top_n_words](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#top_n_words) |

`keybert`는 토픽 문서와 의미적으로 가까운 키워드를 선택합니다. `keybert-mmr`은 같은 과정을 거친 뒤 비슷한 키워드가 반복되지 않도록 다시 정렬합니다. `--keyword-diversity`가 `0`에 가까우면 유사 키워드를 유지하고 `1`에 가까우면 다양성을 더 중시합니다.

### 주제 군집과 이상치 최적화

| 옵션 | 언제 사용하는가 | 기본값 | 공식 문서 |
|---|---|---|---|
| `--umap-neighbors N` | 작게 설정하면 세밀한 구조, 크게 설정하면 전체적인 구조를 중시합니다. | 문서 수에 따라 최대 `15` | [n_neighbors](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#n_neighbors) |
| `--min-samples N` | 낮추면 `-1` 이상치가 감소하지만 관련 없는 문서가 주제에 포함될 수 있습니다. | `min-topic-size`와 동일 | [min_samples](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#min_samples) |
| `--outlier-strategy {none, c-tf-idf, embeddings}` | 학습 후 `-1` 문서를 가장 가까운 기존 주제에 다시 배정합니다. | `none` | [Outlier Reduction Strategies](https://maartengr.github.io/BERTopic/getting_started/outlier_reduction/outlier_reduction.html#strategies) |
| `--outlier-threshold 숫자` | 유사도가 입력값 이상인 이상치만 다시 배정합니다. 0 이상 1 이하로 입력합니다. | `0.1` | [Outlier Reduction](https://maartengr.github.io/BERTopic/getting_started/outlier_reduction/outlier_reduction.html) |
| `--low-memory`, `--no-low-memory` | 기본은 메모리 절약 모드입니다. 메모리가 충분하고 속도를 우선하면 끕니다. | 사용 | [low_memory](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#low_memory) |
| `--calculate-probabilities` | 문서의 주제 배정 확률을 계산합니다. 시간과 메모리 사용량이 크게 늘 수 있습니다. | 사용 안 함 | [calculate_probabilities](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html#calculate_probabilities) |

이상치 재배정은 내부적으로 토픽 생성과 `--reduce-topics` 처리가 끝난 뒤 실행됩니다. 재배정된 문서는 토픽 키워드와 문서 수에도 반영됩니다. 재배정으로 주제가 바뀐 문서에는 기존 확률을 잘못 표시하지 않도록 `topic_probability` 값을 비워 둡니다.

## 상황별 조정 방법

### 주제가 너무 많고 잘게 나뉘는 경우

먼저 `--min-topic-size`를 키웁니다. 그래도 비슷한 주제가 많을 때 `--umap-neighbors`를 `30` 정도로 키우거나 마지막에 `--reduce-topics auto`를 사용합니다.

```powershell
uv run bertopic-cli documents.xlsx `
  --text-columns text `
  --min-topic-size 20 `
  --umap-neighbors 30 `
  --reduce-topics auto
```

### 주제가 너무 적고 크게 묶이는 경우

`--min-topic-size`와 `--umap-neighbors`를 차례로 줄입니다. 한 번에 여러 값을 크게 바꾸지 말고 결과를 비교하는 것이 좋습니다.

```powershell
uv run bertopic-cli documents.xlsx `
  --text-columns text `
  --min-topic-size 5 `
  --umap-neighbors 10
```

### `Outlier` 또는 주제 `-1`이 너무 많은 경우

첫 번째 방법은 `--min-samples`를 `--min-topic-size`보다 작게 설정하는 것입니다. 그래도 이상치가 많고 모든 문서를 분류해야 한다면 `c-tf-idf` 재배정을 추가합니다.

```powershell
uv run bertopic-cli documents.xlsx `
  --text-columns text `
  --min-topic-size 10 `
  --min-samples 5 `
  --outlier-strategy c-tf-idf `
  --outlier-threshold 0.1
```

`embeddings` 방식은 문서 의미를 직접 비교하지만 임베딩을 다시 계산할 수 있어 더 느립니다. 임계값을 너무 낮추면 관련 없는 문서도 억지로 주제에 들어갈 수 있습니다.

### 대표 키워드가 읽기 어려운 경우

불용어 파일, 희귀 단어 제외, 빈출 단어 감소를 먼저 적용하고 필요하면 `keybert-mmr`을 사용합니다.

```powershell
uv run bertopic-cli documents.xlsx `
  --text-columns title abstract `
  --stopwords-file stopwords-ko.txt `
  --min-word-frequency 2 `
  --reduce-frequent-words `
  --representation keybert-mmr `
  --keyword-diversity 0.3
```

### 메모리가 부족한 경우

기본적으로 저메모리 모드가 켜져 있습니다. 추가로 희귀 단어와 전체 어휘 수를 제한하고, 확률 계산과 HTML 시각화를 끕니다.

```powershell
uv run bertopic-cli documents.xlsx `
  --text-columns text `
  --min-word-frequency 2 `
  --max-vocabulary 10000 `
  --no-visualizations
```

## 기타 자주 쓰는 명령

입력 파일의 열 이름을 먼저 확인합니다.

```powershell
uv run bertopic-cli documents.csv --list-columns
```

결과 폴더를 지정합니다.

```powershell
uv run bertopic-cli documents.csv --text-columns text --output results
```

비슷한 주제를 자동으로 합칩니다.

```powershell
uv run bertopic-cli documents.csv --text-columns text --reduce-topics auto
```

모델 또는 시각화를 저장하지 않을 수도 있습니다.

```powershell
uv run bertopic-cli documents.csv --text-columns text --no-save-model --no-visualizations
```

모든 옵션은 도움말에서 확인할 수 있습니다.

```powershell
uv run bertopic-cli --help
```

## 조정할 때 기억할 점

- 한 번에 한두 옵션만 바꾸고 `run_metadata.json`을 함께 보관합니다.
- 토픽 수는 `--reduce-topics`보다 `--min-topic-size`로 먼저 조정하는 것이 안정적입니다.
- `--ngram-max`, 불용어, 단어 빈도, 표현 모델은 대표 키워드를 바꾸지만 문서 군집 자체는 바꾸지 않습니다.
- `--umap-neighbors`, `--min-topic-size`, `--min-samples`, 임베딩 모델은 문서 군집을 바꿀 수 있습니다.
- `--random-seed` 기본값이 `42`이므로 같은 입력과 옵션에서는 결과를 비교하기 쉽습니다.

주제 번호 `-1` 또는 `Outlier`는 어느 주제에도 안정적으로 묶이지 않은 문서이며 오류가 아닙니다.

## BERTopic 공식 참고 문서

- [Parameter tuning](https://maartengr.github.io/BERTopic/getting_started/parameter%20tuning/parametertuning.html)
- [Vectorizers](https://maartengr.github.io/BERTopic/getting_started/vectorizers/vectorizers.html)
- [c-TF-IDF](https://maartengr.github.io/BERTopic/getting_started/ctfidf/ctfidf.html)
- [Representation models](https://maartengr.github.io/BERTopic/getting_started/representation/representation.html)
- [Outlier reduction](https://maartengr.github.io/BERTopic/getting_started/outlier_reduction/outlier_reduction.html)
