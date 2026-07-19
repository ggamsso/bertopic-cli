# BERTopic CLI

Python 코드를 작성하지 않고 CSV, TSV 또는 XLSX 문서를 BERTopic으로 분석하는 명령줄 도구입니다.

## 입력 파일

한 행에 문서 하나가 들어 있는 CSV, TSV 또는 Excel XLSX 파일을 준비합니다.

```csv
id,title,text
1,문서 제목 1,"분석할 첫 번째 문서입니다."
2,문서 제목 2,"분석할 두 번째 문서입니다."
```

분석할 텍스트 열은 `--text-columns`로 반드시 지정합니다. 여러 열을 지정하면 각 행에서 지정 순서대로 합쳐 하나의 문서로 분석합니다. 지정한 열이 입력 파일에 없으면 분석을 시작하지 않고, 누락된 열과 사용 가능한 열을 표시합니다. 열 이름은 대소문자와 공백을 포함해 입력 파일의 이름과 정확히 같아야 합니다.

BERTopic은 문서가 너무 적으면 결과가 불안정합니다. 최소 10개가 필요하며, 가능하면 수십~수백 개 이상을 권장합니다.

## uv로 Python 환경 구축

이 프로젝트는 Python 3.12를 사용합니다. Python과 패키지는 `uv`가 설치하므로 Python을 별도로 설치할 필요가 없습니다.

### Windows 10/11

PowerShell을 열고 `uv`를 설치합니다. Windows Package Manager가 있다면 다음 방법을 권장합니다.

```powershell
winget install --id=astral-sh.uv -e
```

`winget`을 사용할 수 없다면 공식 PowerShell 설치 명령을 사용합니다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

설치가 끝나면 PowerShell을 닫았다가 다시 열고 확인합니다.

```powershell
uv --version
```

프로젝트 폴더로 이동하여 Python 3.12와 프로젝트 패키지를 설치합니다.

```powershell
cd C:\path\to\berttopic
uv python install 3.12
uv sync --locked
```

`uv sync`가 프로젝트 폴더의 `.venv` 가상환경을 만들고 `uv.lock`에 기록된 패키지를 설치합니다.

가상환경을 활성화하지 않고 다음처럼 실행하는 방법을 권장합니다.

```powershell
uv run bertopic-cli ".\data\documents.xlsx" --text-columns "text"
```

시트와 텍스트 열을 지정하는 예시입니다.

```powershell
uv run bertopic-cli ".\data\documents.xlsx" --sheet "논문" --text-columns "title" "abstract"
```

원한다면 PowerShell에서 가상환경을 활성화한 뒤 `bertopic-cli`를 직접 실행할 수도 있습니다.

```powershell
.venv\Scripts\Activate.ps1
bertopic-cli ".\data\documents.xlsx" --text-columns "text"
```

PowerShell 실행 정책 때문에 활성화가 차단되면 환경을 활성화하지 말고 `uv run` 방식을 사용하면 됩니다.

### macOS/Linux

터미널에서 `uv`를 설치합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

터미널을 다시 열고 프로젝트 환경을 구축합니다.

```bash
cd /path/to/berttopic
uv python install 3.12
uv sync --locked
```

실행할 때는 다음처럼 `uv run`을 사용합니다.

```bash
uv run bertopic-cli ./data/documents.xlsx --text-columns text
```

처음 분석할 때 임베딩 모델을 내려받으므로 인터넷 연결이 필요합니다. 파일이나 폴더 경로에 공백이 있으면 경로 전체를 따옴표로 감싸세요.

- [uv 공식 설치 문서](https://docs.astral.sh/uv/getting-started/installation/)
- [uv Python 설치 문서](https://docs.astral.sh/uv/guides/install-python/)
- [uv 프로젝트 동기화 문서](https://docs.astral.sh/uv/concepts/projects/sync/)

## 기본 사용법

```bash
uv run bertopic-cli documents.csv --text-columns text
```

결과는 입력 파일 옆의 `documents_bertopic_results` 폴더에 저장됩니다.

텍스트 열 이름이 `본문`이라면 다음과 같이 실행합니다.

```bash
uv run bertopic-cli documents.csv --text-columns 본문
```

제목과 본문을 함께 분석하려면 컬럼 이름을 원하는 결합 순서대로 나열합니다.

```bash
uv run bertopic-cli documents.csv --text-columns title abstract
```

각 행의 `title`과 `abstract`를 줄바꿈으로 연결해 하나의 문서로 사용합니다. 일부 값이 비어 있으면 존재하는 값만 사용하며, 지정한 컬럼이 모두 비어 있는 행은 분석에서 제외합니다.

영어 문서만 분석한다면 영어 모델과 불용어 설정을 사용합니다.

```bash
uv run bertopic-cli documents.csv --text-columns text --language english
```

Excel 파일도 같은 방법으로 실행할 수 있습니다. 생략하면 첫 번째 시트를 읽습니다.

```bash
uv run bertopic-cli documents.xlsx --text-columns text
```

여러 시트 중 하나를 선택하려면 시트 이름을 지정합니다.

```bash
uv run bertopic-cli documents.xlsx --sheet 설문응답 --text-columns title text
```

## 결과 파일

- `document_topics.csv`: 원본 문서별 주제 번호, 주제 이름, 대표 단어
- `topic_summary.csv`: 주제별 문서 수와 대표 단어
- `topic_barchart.html`: 주제별 대표 단어 그래프
- `topic_map.html`: 주제 사이의 관계를 보여주는 지도
- `model/`: 나중에 재사용할 BERTopic 모델
- `run_metadata.json`: 입력 파일과 실행 설정 기록

CSV 결과는 UTF-8 BOM 형식으로 저장하므로 Excel에서 한글이 깨지지 않습니다.

## 자주 쓰는 옵션

입력 파일의 열 이름을 먼저 확인합니다.

```bash
uv run bertopic-cli documents.csv --list-columns
```

결과 폴더를 지정합니다.

```bash
uv run bertopic-cli documents.csv --text-columns text --output results
```

비슷한 주제를 자동으로 합칩니다.

```bash
uv run bertopic-cli documents.csv --text-columns text --reduce-topics auto
```

모델 또는 시각화를 저장하지 않을 수도 있습니다.

```bash
uv run bertopic-cli documents.csv --text-columns text --no-save-model --no-visualizations
```

모든 옵션은 도움말에서 확인할 수 있습니다.

```bash
uv run bertopic-cli --help
```

## 결과 조정 요령

- 주제가 너무 잘게 나뉨: `--min-topic-size` 값을 키웁니다.
- 대부분 `Outlier`가 됨: `--min-topic-size` 값을 줄입니다.
- 비슷한 주제가 많음: `--reduce-topics auto`를 사용합니다.
- 영어 문서만 있음: `--language english`를 사용합니다.

주제 번호 `-1` 또는 `Outlier`는 어느 주제에도 안정적으로 묶이지 않은 문서이며 오류가 아닙니다.
