# Team10_DigitalCommunication

디지털통신 시스템설계 10조의 프로젝트다. 과제에서 제시한 기준 성상도인 Rectangular 32-QAM과 정수 격자에서 설계한 Type1·Type2·Type3를 비교했다. 동일한 평균 심볼 에너지와 AWGN 조건에서 SER, BER, PAPR, 수신 결정 복잡도, 대칭성을 평가하고 세 가지 통신 시나리오에 적용했다.

## 보고서와 결과

| 자료 | 내용 |
| --- | --- |
| [제출용 통합 보고서](report/FINAL_REPORT.md) | 성상도 설계, 이론과 실험, 시나리오, 결론, 자체평가 양식 |
| [최종 성능 비교 CSV](analysis/final_results/final_comparison.csv) · [산출물 안내](analysis/final_results/README.md) | 공식 4종 × 21개 Eb/N0 지점의 결과, 결정 영역, PAPR·CCDF, 재현 방법 |
| [공식 좌표](data/constellations.csv) · [최적화 매핑](data/mapped_constellations.csv) | 네 방식의 좌표 128행과 5비트 라벨 |
| [이론 SER](results/metrics/theoretical_ser.csv) · [AWGN 관측 SER·BER](results/metrics/simulation_results.csv) | 최근접 근사 및 이론 경계, 초기·최적화 매핑의 Monte Carlo 오류 수와 오류율 |
| [세 시나리오 비교](docs/scenarios/scenario_comparison.md) · [제출 전 검수표](report/SUBMISSION_CHECKLIST.md) | KPI, 선택 근거, 절충, 변경 요청 대응과 제출 확인 항목 |

## 주요 결과

SER과 BER은 **Eb/N0 = 10 dB**의 공식 최적화 매핑 관측값이다. 파형 P99는 RRC roll-off 0.35, 8 SPS에서 프레임별 PAPR의 99백분위수다.

| 성상도 | 관측 SER | 관측 BER | 성상점 PAPR (dB) | 파형 P99 (dB) |
| --- | ---: | ---: | ---: | ---: |
| Rectangular | 0.082457 | 0.016986 | 3.484546 | 6.899573 |
| Type1 | 0.040771 | 0.009320 | 2.304489 | 5.749793 |
| Type2 | 0.044471 | 0.010491 | 2.850419 | 6.051795 |
| Type3 | 0.042924 | 0.009864 | 3.010300 | 6.101589 |

Type1은 위 조건에서 오류율과 PAPR가 가장 낮고, 원점·I축·Q축·90° 회전 대칭을 모두 만족했다. Rectangular의 독립 I/Q 판정은 비교한 수신 구조 중 연산량이 가장 적었다. 오류율 순위는 Eb/N0에 따라 달라진다. 파형 PAPR는 피크 여유를 비교하는 지표이며 실제 PA 비선형 왜곡과 전력 효율은 측정 범위 밖이다.

- **Drone 실시간 영상전송** — 링크 여유가 충분하면 최적화 Type1. [설계 근거](docs/scenarios/scenario_drone.md)
- **산업용 긴급 Alarm** — 기한 내 경보 전달을 우선하는 동기 Gray QPSK. [설계 근거](docs/B_report_draft.md#10-scenario-5-산업용-긴급-alarm)
- **PA 제약 이동단말** — BER 목표, 피크 한계, 수신 처리 예산을 만족하면 최적화 Type1. [설계 근거](docs/scenarios/scenario_pa.md)

## 저장소 구성

| 경로 | 내용 |
| --- | --- |
| `reference/` · `data/` | 과제에서 제시한 Rectangular 기준 좌표, 공식 좌표 및 최적화 매핑 |
| `design/` | 정수 격자 성상도 탐색, 기하 지표 및 이론 SER 계산 |
| `simulation/` | Gray-like 매핑, C++ 실험 코드와 배포된 시뮬레이터 원본에 적용하는 패치 |
| `results/metrics/` · `results/figures/` | 기하·매핑·AWGN 지표, 입력 및 결과 해시, 성상도와 오류율 그래프 |
| `analysis/` | 공식 입력 검증, 결정 영역·PAPR·수신기 분석과 최종 통합 코드 |
| `analysis/final_results/` | 공식 최종 CSV, PNG·PDF, 재현 메타데이터 |
| `analysis/baseline_results/rrc_sweep_verified/` · `analysis/preliminary_results/` | 배포 예제 성상도 기반 기준 실험과 팀 공식 좌표 기반 중간 분석 |
| `docs/` · `report/` | 팀별 설계 문서, 공통 규격, 제출용 통합 보고서 |

## 실행 및 재현

저장소 루트에서 Python 가상환경을 활성화한다.

**macOS**

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Windows 명령 프롬프트에서는 `.venv\Scripts\activate.bat`로 활성화한다.

### 공식 결과 검증과 분석 재현

아래 명령을 순서대로 실행한다. 각 단계가 성공한 뒤 다음 단계로 진행하고, 재실행할 때는 새 출력 디렉터리를 지정한다.

```sh
python -m analysis.validate_final_inputs --receipt results/metrics/optimized_run_receipt.json
python analysis/analyze.py --input data/mapped_constellations.csv --reference data/constellations.csv --out analysis_runs/final_reproduction --waveform-sweep
python -m analysis.integrate_final --out analysis_runs/final_reproduction
python -m unittest analysis.test_analyze -v
```

입력 검증에는 저장소의 공식 CSV와 SHA-256 기록을 사용한다. 해시를 대조할 때는 Git 원본과 같은 LF 줄바꿈을 유지한다. 위 명령은 보존된 B의 AWGN 데이터를 읽어 결정 영역, 파형 분석 및 통합표를 재현한다.

### C++ Monte Carlo 재실행

과제와 함께 배포된 LinkLevelSimulation의 `Source` 사본과 CMake, C++17 컴파일러가 필요하다. 원본 복사, 패치, 빌드 및 실행 순서는 [시뮬레이션 안내](simulation/README.md)에 있으며, 공식 결과 재현 환경과 해시는 [B 실험 인계 기록](docs/B_handoff.md)에서 확인할 수 있다.

## 팀과 협업

| 팀원 | 담당 |
| --- | --- |
| 한규민 | 성상도 설계·기하 분석·이론 SER, Drone |
| 최세용 | Gray-like 매핑·C++ AWGN 실험·SER/BER, Alarm |
| 이주헌 | 결정 영역·PAPR·대칭성·수신 복잡도, PA 시나리오와 결과 통합 |

A의 좌표와 점 식별자를 기준으로 B가 라벨과 오류율을 산출하고, C가 공식 데이터와 실행 해시를 확인해 통합한다. 변경은 담당 브랜치에서 작업한 뒤 `main`을 대상으로 PR 검토를 거친다. [팀 협업 규칙](docs/TEAM_CONVENTIONS.md) · [공통 실험 규격](docs/EXPERIMENT_PROTOCOL.md) · [CSV 규격](docs/DATA_FORMAT.md) · [변경 이력](CHANGELOG.md)

## 제출 상태

공식 성상도 4종의 성능 분석, 세 시나리오의 비교 및 통합 보고서 초안 작성을 완료했다. 제출 전에는 보고서의 작성자 이름·학번과 자체평가 점수를 팀에서 입력하고, 제출 형식에서 수식·표·그림을 확인한다.
