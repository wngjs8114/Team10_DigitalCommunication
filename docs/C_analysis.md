# C 분석 및 검증 기록

## Phase 0 · 소스와 범위

과제 PDF의 필수 비교 지표는 SER, BER, PAPR, 수신 결정 복잡도, 대칭성이다. 보고서 4.1은 SER·BER 결정 경계를, 7.3은 PAPR 실험 분석을 요구한다. RRC 파형 PAPR 및 CCDF는 추가 연구로 진행한다. PDF에서 10조에 배정한 Drone 영상전송, 산업용 긴급 Alarm, PA 제약 이동단말을 확인했다.

`analysis/analyze.py`는 `Team10_C_v1.zip`의 `src/analyze.py`를 이관한 파일이다. ZIP과 압축 해제본의 코드 및 입력 CSV가 각각 바이트 단위로 일치함을 확인했다. `analysis/baseline/`의 CSV는 교수님 제공 `LinkLevelSimulation.zip` 내부의 `QAM32.cpp`에 있는 네 성상도 예제와 128개 원본 좌표가 식별자 순서까지 일치한다. 이 CSV의 비트는 예제 인덱스의 5자리 이진 표현이다. A의 제안 성상도와 B의 최종 Mapping 및 실험 결과는 팀 전달 후 적용한다.

- 기준 CSV SHA-256은 `d539c52219174514428fd80163ccdab3e8f18fe8ff9a04bd6a31e830ba0a8302`이다.
- 교수 제공 ZIP SHA-256은 `c1f53e5c882fa1e69a3b59a7f46b4cbf0aab9a2d188e0055c63149c2abd5c87a`이다.

## Phase 1 · 실행 방법

저장소 루트에서 가상환경을 활성화하고 `python -m pip install -r requirements.txt`로 설치한다. 각 실행의 `--out`은 새 경로를 사용한다.

```sh
python analysis/analyze.py --baseline --input analysis/baseline/baseline_mapped_constellations.csv --out baseline_runs/metrics --metrics-only
python -m unittest analysis.test_analyze -v
```

`--metrics-only`를 빼면 PNG와 PDF 그림을 생성한다. `--waveform`을 추가하면 프레임별 RRC 파형 PAPR 및 CCDF도 생성한다. 팀 데이터가 확보되면 아래 명령으로 B의 좌표와 식별자를 A의 CSV에 대조할 수 있다. A의 CSV만 입력하면 심볼 지표 및 SER 결정 영역을 계산한다.

```sh
python analysis/analyze.py --input data/mapped_constellations.csv --reference data/constellations.csv --out analysis_runs/team
```

## 검증 결과와 한계

- Rectangular 원본 평균 에너지는 I축의 5와 Q축의 21을 더한 26이며 최대 에너지는 58이다. 모든 점을 동일한 계수로 스케일하면 전력의 공통 배율이 분자·분모에서 상쇄된다. 실행 결과는 평균 정규화 에너지 1, 최소거리 0.392232, PAPR 58/26 = 2.230769, 3.484546 dB였다.
- 대칭성은 정수 좌표 집합을 변환해 검사한다. Rectangular는 원점 및 I/Q축 반사 대칭이 있고, 90도 회전 대칭은 없다. 중심이 원점이라는 조건만으로 원점 대칭이 보장되지는 않는다.
- 수신기 검증은 동일한 난수 수신점 10,000개를 네 성상도에 적용했다. 최소 제곱거리와 동률이 아닌 판정 인덱스가 모두 일치했다. 별도 단위 테스트에서 원점의 동률 처리도 확인했다. 그룹 내 Q 탐색 비용이 있으므로 열별 최종 후보 수만으로 연산량 감소를 판단할 수 없다. 네 방식의 전수 ML은 모두 거리 평가 32회와 후보 비교 31회다.
- 기존 경계 그림은 401×401 격자에서 계산하며 격자 간격은 0.01이다. 기본 BER 그림은 심볼 ML 결정 영역에 각 비트 라벨을 입힌다. 정확한 Voronoi 기하와 연산 계수 비교는 후속 검증 항목이다.
- `receiver_complexity.csv`에 수신점 수와 동률·판정 인덱스 불일치 수를 기록한다. `waveform_papr.csv`는 `scheme,frame,papr_db`를 사용한다. 실행 당시의 입력 해시, 시드와 주요 반복 조건은 `run_metadata.json`에 기록한다.
- RRC 조건은 roll-off 0.35, 8 samples/symbol, span 10 심볼, 프레임당 512 측정 심볼, 앞뒤 각 8 가드 심볼, 2,000프레임, 시드 2026이다. 필터 길이·대칭·단위 에너지, 그리고 동률이 있는 표본에서 엄격한 초과 확률 `P(PAPR > x)`를 단위 테스트했다. 전체 컨볼루션 및 그래프 재현은 SciPy·Matplotlib 설치 후 확인한다.
- 기준 실험 지표와 단위 테스트는 Python 3.12, NumPy 2.3.5, pandas 2.2.3으로 검증했다.
