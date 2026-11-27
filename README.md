# Team10_DigitalCommunication

디지털통신 시스템설계 10조의 **32-QAM Constellation Optimization and Digital Communication System Design** 프로젝트다. Python과 C++로 세 가지 후보 성상도와 교수님이 제공한 Rectangular 기준 성상도를 비교한다.

## 설계 목표

평균 심볼 에너지를 통일한 AWGN 조건에서 성상점 배치와 비트 Mapping이 SER·BER에 미치는 영향을 비교한다. PAPR, 대칭성, 수신 결정 복잡도를 함께 평가해 Drone 실시간 영상전송, 산업용 긴급 Alarm, PA 제약 이동형 단말에 적합한 설계를 검토한다.

## 팀원별 역할

| 팀원 | 브랜치 | 역할 |
| --- | --- | --- |
| 한규민 | `feature/design` | 성상도 최적화, 기하 특성 및 이론적 SER, Drone 시나리오 |
| 최세용 | `feature/simulation` | Gray-like Mapping, C++ 시뮬레이터 및 SER·BER, Alarm 시나리오 |
| 이주헌 | `feature/analysis` | PAPR·대칭성·결정 경계·수신 복잡도, PA 시나리오 및 결과 통합 |

## 파일 구조

```text
Team10_DigitalCommunication/
├── reference/
│   └── .gitkeep
├── data/
│   ├── README.md
│   └── .gitkeep
├── design/
│   └── README.md
├── simulation/
│   └── README.md
├── analysis/
│   └── README.md
├── results/
│   ├── metrics/
│   │   └── .gitkeep
│   └── figures/
│       ├── constellations/
│       │   └── .gitkeep
│       ├── ser_decision_boundaries/
│       │   └── .gitkeep
│       └── ber_decision_boundaries/
│           └── .gitkeep
├── docs/
│   ├── TEAM_CONVENTIONS.md
│   ├── EXPERIMENT_PROTOCOL.md
│   ├── DATA_FORMAT.md
│   └── scenarios/
│       └── .gitkeep
├── report/
│   └── .gitkeep
├── .editorconfig
├── .gitignore
├── AGENTS.md
├── README.md
├── CHANGELOG.md
└── requirements.txt
```

## 개발 환경

저장소를 복제한 뒤 프로젝트 루트에서 Python 가상환경을 생성하고 패키지를 설치한다.

### macOS

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Windows 명령 프롬프트에서는 `.venv\Scripts\activate.bat`로 활성화한다. Python 패키지 버전은 실제 실행 환경을 검증한 뒤 확정한다. C++ 컴파일러 및 빌드·실행 방법은 교수님 제공 시뮬레이터를 확인한 뒤 문서화할 예정이다.

## GitHub 협업

먼저 `git fetch origin`을 실행한다. 담당 브랜치를 처음 만들 때는 `git switch -c feature/analysis origin/main`처럼 자기 브랜치 이름을 사용한다. 기존 브랜치에서 작업을 재개할 때는 담당 브랜치로 전환하고 `git merge origin/main`으로 최신 통합 내용을 반영한다. 변경을 커밋하고 담당 브랜치를 push한 뒤 `main`을 대상으로 PR을 열어 검토받는다.

## 데이터 전달 순서

1. A는 `data/constellations.csv`에 확정 성상점과 정규화 좌표를 기록해 B와 C에 전달한다.
2. B는 좌표와 `point_id`를 유지한 `data/mapped_constellations.csv`와 SER·BER 실험 결과를 C에 전달한다.
3. C는 성상도와 Mapping을 사용해 분석하고 A의 기하 지표 및 B의 실험 지표를 종합한다. 각 실험에서 사용한 입력 데이터의 Git 커밋 ID 또는 해시를 남긴다.

## 공통 문서

- [협업 및 그래프 규칙](docs/TEAM_CONVENTIONS.md)
- [실험 규격](docs/EXPERIMENT_PROTOCOL.md)
- [CSV 규격](docs/DATA_FORMAT.md)
- [AI 코딩 에이전트 규칙](AGENTS.md)
- [변경 이력](CHANGELOG.md)

## 진행 상태

저장소 구조와 공통 규격을 초기화했다. 성상도 최적화, Mapping, C++ 시뮬레이션, 성능 분석 및 Part B 시나리오 문서는 구현 예정이다. 교수님 제공 기준 성상도와 시뮬레이터는 파일을 확보한 뒤 확인한다.
