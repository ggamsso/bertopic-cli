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

문서 폴더로 이동한 뒤, 교육 담당자가 제공한 Git 저장소 주소를 붙여넣습니다.

```powershell
cd "$HOME\Documents"
$repo = Read-Host "Git 저장소 주소를 붙여넣으세요"
git clone $repo berttopic
cd ".\berttopic"
```

이미 `berttopic` 프로젝트 폴더를 전달받았다면 `git clone`은 생략하고 해당 폴더로 이동합니다.

```powershell
cd "C:\실제\berttopic\폴더\경로"
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
cd "$HOME\Documents\berttopic"
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
berttopic\data\papers.xlsx
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

- `document_topics.csv`: 원본 문서별 주제 번호, 주제 이름, 대표 단어
- `topic_summary.csv`: 주제별 문서 수와 대표 단어
- `topic_barchart.html`: 주제별 대표 단어 그래프
- `topic_map.html`: 주제 사이의 관계를 보여주는 지도
- `model/`: 나중에 재사용할 BERTopic 모델
- `run_metadata.json`: 입력 파일과 실행 설정 기록

CSV 결과는 UTF-8 BOM 형식으로 저장하므로 Excel에서 한글이 깨지지 않습니다.

## 자주 쓰는 옵션

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

## 결과 조정 요령

- 주제가 너무 잘게 나뉨: `--min-topic-size` 값을 키웁니다.
- 대부분 `Outlier`가 됨: `--min-topic-size` 값을 줄입니다.
- 비슷한 주제가 많음: `--reduce-topics auto`를 사용합니다.
- 영어 문서만 있음: `--language english`를 사용합니다.

주제 번호 `-1` 또는 `Outlier`는 어느 주제에도 안정적으로 묶이지 않은 문서이며 오류가 아닙니다.
