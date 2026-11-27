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

`--metrics-only`를 빼면 PNG와 PDF 그림을 생성한다. `--waveform`을 추가하면 프레임별 RRC 파형 PAPR 및 CCDF도 생성한다. 전체 roll-off·샘플링 비교는 다음 명령으로 실행한다.

```sh
python analysis/analyze.py --baseline --input analysis/baseline/baseline_mapped_constellations.csv --out baseline_runs/rrc_sweep --waveform-sweep
```

팀 데이터가 확보되면 아래 명령으로 B의 좌표와 식별자를 A의 CSV에 대조할 수 있다. A의 CSV만 입력하면 심볼 지표 및 SER 결정 영역을 계산한다.

```sh
python analysis/analyze.py --input data/mapped_constellations.csv --reference data/constellations.csv --out analysis_runs/team
```

## Baseline 실험 결과

macOS 가상환경의 NumPy 2.5.5, pandas 3.1.1, SciPy 1.18.1, Matplotlib 3.11.2에서 재실행했다. 정규화 좌표는 CSV 토큰을 Python `float`로 직접 변환한다. 기준 좌표 전체의 binary64 값과 A/B 좌표 대조에서 한 ULP 차이가 검출되는지 확인했다.

| Scheme | 성상점 PAPR (dB) | 프레임 평균 (dB) | 95백분위수 (dB) | 99백분위수 (dB) |
| --- | ---: | ---: | ---: | ---: |
| Rectangular | 3.484546 | 6.215514 | 6.675754 | 6.899573 |
| Type1 | 3.767507 | 5.895643 | 6.457335 | 6.748380 |
| Type2 | 2.850419 | 5.444090 | 5.925327 | 6.176144 |
| Type3 | 3.679768 | 5.902218 | 6.476827 | 6.802756 |

파형 열은 roll-off 0.35, 8 SPS 조건의 프레임별 dB 값이다. 평균은 dB 값의 산술평균이며 백분위수는 선형 보간으로 구했다. 기존 `analysis/baseline_results/waveform_papr.csv`와 8,000개 프레임 결과가 읽어들인 값 기준으로 모두 일치했다.

Rectangular 원본 평균 에너지는 I축의 5와 Q축의 21을 더한 26이며 최대 에너지는 58이다. 정규화의 공통 전력 배율은 분자·분모에서 상쇄된다. 정규화 후 평균 에너지 1, 최소거리 0.392232, PAPR 58/26 = 2.230769를 확인했다. 정수 좌표 집합에서 원점 및 I/Q축 반사 대칭을 확인했고 90도 회전에서는 좌표 집합이 달라졌다. 평균 좌표가 0인 성상도도 원점 대칭은 별도로 검사한다.

## 수신 결정 복잡도

아래는 수신 심볼 1개당 산술·비교 연산의 이론적 개수다. 그룹·축 목록과 Cartesian 조합에서 심볼로 변환하는 표는 미리 만든다. 배열 접근, 인덱싱, 사전 계산, SIMD·FMA 및 실제 실행시간은 집계 범위 밖이다.

| 수신기 | 뺄셈 | 덧셈 | 곱셈 | 비교 |
| --- | ---: | ---: | ---: | ---: |
| 전수 ML, 전 방식 | 64 | 32 | 64 | 31 |
| 그룹 ML, Rectangular | 36 | 4 | 36 | 31 |
| 그룹 ML, Type1 | 38 | 6 | 38 | 31 |
| 그룹 ML, Type2 | 39 | 7 | 39 | 31 |
| 그룹 ML, Type3 | 40 | 8 | 40 | 31 |
| I/Q 독립 선형 탐색, Rectangular | 12 | 0 | 12 | 10 |

그룹 ML은 32개 점의 Q 거리 제곱을 계산하고, I 좌표가 같은 열 안에서 최소 Q 항을 찾는다. 열이 G개일 때 열 내부 비교는 32−G회, 열 사이 비교는 G−1회다. 선택한 Q 항을 재사용해 열별 I 거리 제곱을 더한다. Rectangular는 모든 I/Q 조합이 존재하므로 각 축을 독립적으로 최소화해도 전체 제곱거리의 최소가 된다. 세 구현 모두 조기 종료 없는 선형 탐색이므로 평균과 최악 연산 수가 동일하다.

공통 난수 수신점 10,000개에서 네 기준 성상도의 그룹 ML, 그리고 Rectangular 독립 I/Q 모두 전수 ML과 최소거리 및 판정이 일치했다. 원점 동률은 별도로 테스트했다. 판정 검증은 `receiver_complexity.csv`, 연산 수는 `receiver_operation_counts.csv`에 기록한다.

## RRC roll-off 및 oversampling

같은 시드 2026의 심볼 인덱스 배열을 모든 성상도와 조건에서 공유한다. roll-off 0.15·0.35·0.60과 4·8·16·32 SPS의 전 조합을 각 2,000프레임에서 측정했다. 필터 span은 10심볼이며 군지연 5심볼을 보상하고, 앞뒤 8심볼 가드 사이 중앙 512심볼만 집계한다. 직접 영삽입·컨볼루션과 결과를 비교하고 가드 바깥 심볼을 바꿔도 측정 구간이 동일함을 테스트했다.

| SPS | 평균의 최대 차이 (dB) | 95백분위수의 최대 차이 (dB) | 99백분위수의 최대 차이 (dB) |
| --- | ---: | ---: | ---: |
| 4 | 0.06853 | 0.05581 | 0.06930 |
| 8 | 0.01935 | 0.02468 | 0.02666 |
| 16 | 0.00826 | 0.01172 | 0.00496 |

차이는 각 성상도·roll-off 조합에서 32 SPS를 기준으로 계산한 절대차의 최댓값이다. 이 실험에서는 SPS 증가에 따라 요약 지표가 32 SPS에 가까워졌다. 32 SPS 자체도 샘플 기반 근사다.

8 SPS에서 roll-off 0.15는 네 방식 모두 0.35보다 평균과 99백분위수가 높았다. 0.60에서는 네 방식 모두 99백분위수가 낮아졌지만 평균은 Type1·Type2·Type3에서 높아졌다. Rectangular는 성상점 PAPR 기준 두 번째로 낮지만 기본 파형 조건에서는 평균과 99백분위수가 가장 높았다. RRC 펄스가 겹치면서 주변 심볼의 크기와 위상에 따라 보강·상쇄가 일어나며, 심볼 시각 사이의 피크와 프레임 평균 전력이 함께 변할 수 있다. 이 실험에는 PA 비선형성과 실제 장비의 전력효율 측정이 포함되지 않았다.

`waveform_papr.csv`와 CCDF 그림은 기존 기본 조건을 유지한다. `waveform_papr_summary.csv`는 `scheme,roll_off,samples_per_symbol,frames,mean_papr_db,p95_papr_db,p99_papr_db`를 기록한다. `run_metadata.json`에는 기준 입력 해시, 시드와 실험 조건을 남긴다.

## 결정 영역 및 그래프 검증

기존 401×401 격자 보간을 수직이등분선 반평면의 교집합으로 바꿨다. 각 다각형 꼭짓점에서 해당 심볼이 최소 제곱거리를 달성하는지 확인했고, 면적 합은 네 성상도 모두 표시 범위 면적 16이었다. BER 그림은 같은 심볼 ML 다각형을 비트별로 색칠한다. 기준 라벨을 사용한 그림에는 baseline을 표기한다. 흰 배경, 영어 축·제목, 고정 I/Q 범위와 1:1 종횡비, 팀 색·마커, 로그 CCDF, PNG 300 DPI와 벡터 PDF를 확인했다. CCDF의 0값은 로그 축에서 생략한다. 단위 테스트 9개가 통과했다.
