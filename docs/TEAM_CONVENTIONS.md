# 팀 협업 규칙

| 브랜치 | 담당 |
| --- | --- |
| `main` | 검증된 통합 결과물 |
| `feature/design` | A |
| `feature/simulation` | B |
| `feature/analysis` | C |

작업 시작 전에 최신 `main`을 자신의 담당 브랜치에 반영한다. 작업 완료 후 `main`을 대상으로 Pull Request를 열고 검토를 거쳐 병합한다. `main`에 직접 push하거나 force push하지 않는다. 다른 팀원의 담당 경로나 파일은 해당 팀원과 협의 후 수정한다. 성상점 좌표 또는 Mapping이 바뀌면 전원에게 공유한다. 실험에 사용한 입력 데이터의 Git 커밋 ID 또는 해시를 기록한다.

## 담당 경로와 업무

### A · 성상도 설계 및 최적화

- `design/`, `data/constellations.csv`
- `results/metrics/geometry_metrics.csv`, `results/figures/constellations/`
- `docs/A_design.md`, `docs/scenarios/scenario_drone.md`

Type1·Type2·Type3 성상도를 탐색·최적화하고 정규화, 최소거리, 최근접 이웃 및 이론적 SER을 분석한다. Part B에서는 Drone 실시간 영상전송을 담당한다.

### B · Mapping 및 시뮬레이션

- `simulation/`, `data/mapped_constellations.csv`
- `results/metrics/mapping_metrics.csv`, `results/metrics/simulation_results.csv`
- `results/figures/ser_comparison.png`, `results/figures/ber_comparison.png`
- `docs/B_simulation.md`, `docs/scenarios/scenario_alarm.md`

Gray-like Mapping을 최적화하고 교수님이 제공한 C++ 시뮬레이터를 수정해 SER과 BER을 실험한다. Part B에서는 산업용 긴급 Alarm을 담당한다.

### C · 성능 분석 및 결과 통합

- `analysis/`
- `results/metrics/constellation_metrics.csv`, `results/metrics/receiver_complexity.csv`
- `results/metrics/waveform_papr.csv`, `results/metrics/final_comparison.csv`
- `results/figures/papr_comparison.png`, `results/figures/papr_ccdf.png`
- `results/figures/ser_decision_boundaries/`, `results/figures/ber_decision_boundaries/`
- `docs/C_analysis.md`, `docs/scenarios/scenario_pa.md`, `docs/scenarios/scenario_comparison.md`

PAPR, 성상도 대칭성, SER·BER Decision Boundary와 수신 결정 복잡도를 분석한다. RRC Pulse Shaping과 PAPR CCDF 추가 실험을 수행하고 전체 성능을 종합 비교한다. Part B에서는 PA 제약 이동형 단말을 담당한다.

## 커밋 메시지

`유형: 변경 요약` 형식을 사용한다.

| 유형 | 용도 |
| --- | --- |
| `feat` | 새로운 기능 |
| `fix` | 오류 수정 |
| `data` | 데이터 변경 |
| `docs` | 문서 수정 |
| `refactor` | 코드 구조 개선 |
| `test` | 테스트 추가 |
| `chore` | 개발 환경 및 프로젝트 설정 |

## Python 코드

- 변수와 함수는 `snake_case`, 클래스는 `PascalCase`, 상수는 `UPPER_CASE`를 사용한다.
- 경로는 `pathlib`로 처리하고 절대 경로를 하드코딩하지 않는다.
- 프로젝트 루트에서 실행 가능하게 구성하고 입력과 출력을 분리한다.
- CLI 인자로 입력 및 출력 경로를 바꿀 수 있게 설계한다.

## 그래프

| Scheme | 색상 | 마커 |
| --- | --- | --- |
| Rectangular | `#64748B` | 원형 (`o`) |
| Type1 | `#2563EB` | 사각형 (`s`) |
| Type2 | `#0D9488` | 삼각형 (`^`) |
| Type3 | `#9333EA` | 마름모 (`D`) |

- 배경은 흰색으로 통일한다. 제목과 축 이름은 영어로 쓰고, 단위와 범례를 표시한다.
- SER 및 BER의 Y축은 로그 스케일로 표시한다. 오류 0회 관측값은 임의의 작은 값으로 대체하지 않으며, 로그 축에 표시할 수 없는 점은 주석 등으로 관측 사실을 명시한다.
- 성상도 I/Q축의 단위 길이를 동일하게 유지한다. 비교 그래프의 축 범위는 가능한 한 통일한다.
- PNG는 300 DPI로 저장하고 PDF는 벡터 형식으로 저장한다.
