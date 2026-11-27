# C 분석 및 검증 기록

이 문서의 수치와 그림은 교수님이 제공한 예제 성상도와 기준 매핑으로 검증한 **baseline**이다. 팀의 최종 설계 비교는 A/B 산출물과 실행 당시 버전 증거를 확보한 뒤 작성한다.

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

## 최종 데이터 적용 절차

A와 B의 PR이 `main`에 병합되면 깨끗한 `feature/analysis` 작업 트리에서 `git fetch origin`과 `git merge origin/main`으로 최신 입력을 가져온다. `git rev-parse HEAD`를 실행 기록에 남긴다.

| 입력 | 검증 및 사용 |
| --- | --- |
| `data/constellations.csv` | A의 좌표·식별자, Scheme별 점 수·중복·좌표 제한, 정규화 및 평균 심볼 에너지 확인 |
| `data/mapped_constellations.csv` | A의 `(scheme, point_id)` 및 원본·정규화 좌표와 일치하는지 확인. 5자리 비트 라벨의 선행 0 및 전단사 확인 |
| `results/metrics/geometry_metrics.csv` | A의 평균 원본 에너지, 정규화 계수, 최소거리를 좌표에서 재계산해 대조. 최근접 이웃 평균은 A의 이웃 정의와 함께 해석 |
| `results/metrics/simulation_results.csv` | B의 `optimized` 결과를 최종 SER·BER 비교에 사용. `initial` 행은 매핑 개선 전 비교용으로 보관 |
| `results/metrics/mapping_metrics.csv` | B의 `mapping` 열로 최적화 전후 해밍 거리와 Gray edge 비율을 구분 |

B로부터 **최적화 매핑 실험 당시** 사용한 두 입력 CSV와 그 실행 결과 CSV 두 개의 SHA-256을 받는다. 실험 기록이 Git 커밋 ID를 제공한다면 해당 커밋의 파일 바이트에서 해시를 계산한다. 현재 파일에서 해시를 새로 생성하는 것만으로는 과거 실험의 입력 버전을 증명할 수 없다. 영수증 JSON은 아래 네 저장소 상대 경로를 키로 하고 각 값에는 해당 파일의 SHA-256 문자열을 넣는다.

- `data/constellations.csv`
- `data/mapped_constellations.csv`
- `results/metrics/simulation_results.csv`
- `results/metrics/mapping_metrics.csv`

B의 실행 기록에서 공통 AWGN·ML 조건, Eb/N0 정의, `optimized`가 전달된 Mapping과 동일함을 확인한다. 그 뒤 아래 명령을 저장소 루트에서 실행한다. 첫 명령이 통과해야 분석이 실행된다.

```sh
python -m analysis.validate_final_inputs --receipt analysis_runs/optimized_receipt.json && \
python analysis/analyze.py \
  --input data/mapped_constellations.csv \
  --reference data/constellations.csv \
  --out analysis_runs/final_optimized \
  --waveform-sweep
```

검증기는 5개 CSV의 존재 여부, 버전 해시, 두 좌표 파일의 일치, 기하 지표, 비트 라벨, 오류 카운트와 SER·BER의 일관성, 네 방식의 최적화 결과가 공통 0–20 dB 그리드를 만족하는지 확인한다. 기하 지표의 재계산 대조 허용차는 절대값 `1e-6`이다. 팀이 다른 SNR 범위나 출력 정밀도를 합의하면 실험 기록과 검증 조건을 함께 갱신한다.

최종 비교표에서는 동일한 Eb/N0에서 **SER과 BER을 각각** 비교하고, 순위가 바뀌면 SNR 구간을 구분한다. 독립 반복을 합칠 때는 중복 기록 여부와 시드를 확인한 후 오류 수 합을 해당 분모 합으로 나눈다. 초기 매핑 결과에는 해당 매핑의 별도 버전 증거를 확인한 뒤 개선 전후 비교에만 사용한다. 오류 0회는 표본 수와 함께 기록한다. 최종 비교표는 실제 팀 데이터 검증 후 작성한다.

## 4.1 결정 경계

AWGN에서 심볼 사전확률이 같으면 조건부 밀도는 \(\exp(-|r-s_k|^2/N_0)\)에 비례하므로 ML 판정은 제곱거리를 최소화한다. 후보 \(s_i\)가 \(s_j\)보다 가깝다는 조건은 \(2r\cdot(s_j-s_i)\le |s_j|^2-|s_i|^2\)인 반평면이다. 판정 영역은 모든 경쟁점에 대한 반평면의 교집합이다.

기존 401×401 격자 보간을 수직이등분선 반평면의 교집합으로 바꿨다. 각 다각형 꼭짓점에서 해당 심볼이 최소 제곱거리를 달성하는지 확인했고, 면적 합은 네 성상도 모두 표시 범위 면적 16이었다. BER 그림은 같은 심볼 ML 다각형을 비트별로 색칠한다. 기준 라벨을 사용한 그림에는 baseline을 표기한다. 흰 배경, 영어 축·제목, 고정 I/Q 범위와 1:1 종횡비, 팀 색·마커, 로그 CCDF, PNG 300 DPI와 벡터 PDF를 확인했다. CCDF의 0값은 로그 축에서 생략한다. 단위 테스트 9개가 통과했다.

## 4.4 PAPR

정규화 좌표 \(s_k=I_k+jQ_k\)에서 심볼 전력은 \(|s_k|^2\)에 비례한다. 성상점 PAPR는 32개 좌표의 최대 에너지를 균등 발생 시 평균 에너지로 나눈 값이다. Rectangular에서 원본 평균 에너지는 I축 5와 Q축 21을 더한 26이며 최대는 58이다. 정규화의 공통 배율 \(1/26\)이 분자·분모에서 상쇄되어 \(10\log_{10}(58/26)=3.484546\) dB를 얻는다. 정규화 평균 에너지 1과 최소거리 0.392232를 실행에서 확인했다.

RRC 송신 파형은 \(x(t)=\sum_k s_k p(t-kT)\)다. 여기서 \(p(t)\)는 송신 RRC 펄스, \(T\)는 심볼 주기다. \(|x(t)|^2\)에는 각 심볼의 에너지 항과 서로 다른 심볼 사이의 복소 교차항이 포함된다. 교차항은 상대 위상과 펄스 겹침에 따라 양수 또는 음수가 될 수 있다. 파형 PAPR의 분모는 같은 프레임 측정 구간의 평균 전력이고, 분자는 그 구간의 최대 전력이다. 따라서 성상점의 최대·평균 에너지 비만으로 파형 순위를 정할 수 없다.

## 4.5 구현 복잡도

아래는 수신 심볼 1개당 산술·비교 연산의 이론적 개수다. 그룹·축 목록과 Cartesian 조합에서 심볼로 변환하는 표는 미리 만든다. 배열 접근, 인덱싱, 사전 계산, SIMD·FMA 및 실제 실행시간은 집계 범위 밖이다.

| 수신기 | 뺄셈 | 덧셈 | 곱셈 | 비교 |
| --- | ---: | ---: | ---: | ---: |
| 전수 ML, 전 방식 | 64 | 32 | 64 | 31 |
| 그룹 ML, Rectangular | 36 | 4 | 36 | 31 |
| 그룹 ML, Type1 | 38 | 6 | 38 | 31 |
| 그룹 ML, Type2 | 39 | 7 | 39 | 31 |
| 그룹 ML, Type3 | 40 | 8 | 40 | 31 |
| I/Q 독립 선형 탐색, Rectangular | 12 | 0 | 12 | 10 |

수신점을 \(r=(r_I,r_Q)\), 각 I열의 Q 후보 집합을 \(Q_i\)라고 두면 전수 ML의 최소 제곱거리는 \(\min_i[(r_I-i)^2+\min_{q\in Q_i}(r_Q-q)^2]\)와 같다. 열 안에서는 I 항이 상수다. Rectangular에서는 모든 열이 같은 Q 후보 집합을 공유하므로 두 축의 최소화가 분리된다.

그룹 ML은 32개 점의 Q 거리 제곱을 계산하고, I 좌표가 같은 열 안에서 최소 Q 항을 찾는다. 열이 G개일 때 열 내부 비교는 32−G회, 열 사이 비교는 G−1회다. 선택한 Q 항을 재사용해 열별 I 거리 제곱을 더한다. Rectangular는 모든 I/Q 조합이 존재하므로 각 축을 독립적으로 최소화해도 전체 제곱거리의 최소가 된다. 세 구현 모두 조기 종료 없는 선형 탐색이므로 평균과 최악 연산 수가 동일하다.

공통 난수 수신점 10,000개에서 네 기준 성상도의 그룹 ML, 그리고 Rectangular 독립 I/Q 모두 전수 ML과 최소거리 및 판정이 일치했다. 원점 동률은 별도로 테스트했다. 판정 검증은 `receiver_complexity.csv`, 연산 수는 `receiver_operation_counts.csv`에 기록한다.

## 4.6 대칭성

원본 정수 좌표 집합을 원점 반전 \((-I,-Q)\), I축 반사 \((I,-Q)\), Q축 반사 \((-I,Q)\), 90도 회전 \((-Q,I)\)으로 변환한 후 집합 일치 여부를 검사한다. Rectangular는 원점과 양 축 반사 대칭을 만족하며 90도 회전에서는 집합이 달라진다. 원점 대칭이면 균등 발생 조건에서 평균은 0이지만, 평균 0만으로 점별 대칭 쌍의 존재가 보장되지는 않는다.

## 7.3 PAPR 실험 분석 · baseline

macOS 가상환경의 NumPy 2.5.5, pandas 3.1.1, SciPy 1.18.1, Matplotlib 3.11.2에서 재실행했다. 정규화 좌표는 CSV 토큰을 Python `float`로 직접 변환한다. 기준 좌표 전체의 binary64 값과 A/B 좌표 대조에서 한 ULP 차이가 검출되는지 확인했다.

| Scheme | 성상점 PAPR (dB) | 프레임 평균 (dB) | 95백분위수 (dB) | 99백분위수 (dB) |
| --- | ---: | ---: | ---: | ---: |
| Rectangular | 3.484546 | 6.215514 | 6.675754 | 6.899573 |
| Type1 | 3.767507 | 5.895643 | 6.457335 | 6.748380 |
| Type2 | 2.850419 | 5.444090 | 5.925327 | 6.176144 |
| Type3 | 3.679768 | 5.902218 | 6.476827 | 6.802756 |

파형 열은 roll-off 0.35, 8 SPS 조건의 프레임별 dB 값이다. 평균은 dB 값의 산술평균이며 백분위수는 선형 보간으로 구했다. 기존 `analysis/baseline_results/waveform_papr.csv`와 8,000개 프레임 결과가 읽어들인 값 기준으로 모두 일치했다.

### 7.3 추가 실험 · RRC roll-off 및 oversampling

같은 시드 2026의 심볼 인덱스 배열을 모든 성상도와 조건에서 공유한다. roll-off 0.15·0.35·0.60과 4·8·16·32 SPS의 전 조합을 각 2,000프레임에서 측정했다. 필터 span은 10심볼이며 군지연 5심볼을 보상하고, 앞뒤 8심볼 가드 사이 중앙 512심볼만 집계한다. 직접 영삽입·컨볼루션과 결과를 비교하고 가드 바깥 심볼을 바꿔도 측정 구간이 동일함을 테스트했다.

| SPS | 평균의 최대 차이 (dB) | 95백분위수의 최대 차이 (dB) | 99백분위수의 최대 차이 (dB) |
| --- | ---: | ---: | ---: |
| 4 | 0.06853 | 0.05581 | 0.06930 |
| 8 | 0.01935 | 0.02468 | 0.02666 |
| 16 | 0.00826 | 0.01172 | 0.00496 |

차이는 각 성상도·roll-off 조합에서 32 SPS를 기준으로 계산한 절대차의 최댓값이다. 이 실험에서는 SPS 증가에 따라 요약 지표가 32 SPS에 가까워졌다. 연속인 유한 프레임 파형을 같은 구간에서 더 촘촘하게 샘플링하면, 샘플 최대 전력은 구간의 최고 전력에 접근하고 평균 전력은 시간 평균의 리만 합에 접근한다. 평균 전력이 양수이면 두 추정량의 비도 파형 PAPR에 접근한다. 분모도 SPS에 따라 변하므로 각 프레임의 PAPR가 단조 증가할 필요는 없다. 32 SPS는 이번 수치 비교의 기준이다.

8 SPS에서 roll-off 0.15는 네 방식 모두 0.35보다 평균과 99백분위수가 높았다. 0.60에서는 네 방식 모두 99백분위수가 낮아졌지만 평균은 Type1·Type2·Type3에서 높아졌다. Rectangular는 성상점 PAPR 기준 두 번째로 낮지만 기본 파형 조건에서는 평균과 99백분위수가 가장 높았다. RRC 펄스가 겹치면서 주변 심볼의 크기와 위상에 따라 보강·상쇄가 일어나며, 심볼 시각 사이의 피크와 프레임 평균 전력이 함께 변할 수 있다. 이 실험에는 PA 비선형성과 실제 장비의 전력효율 측정이 포함되지 않았다.

`waveform_papr.csv`와 CCDF 그림은 기존 기본 조건을 유지한다. `waveform_papr_summary.csv`는 `scheme,roll_off,samples_per_symbol,frames,mean_papr_db,p95_papr_db,p99_papr_db`를 기록한다. `run_metadata.json`에는 기준 입력 해시, 시드와 실험 조건을 남긴다.

## 8. 정성적 비교

기준 실험에서 Type2의 성상점 PAPR와 기본 조건 파형 PAPR가 모두 가장 낮았다. 같은 조건에서 Rectangular는 독립 I/Q 판정으로 산술 연산과 비교를 줄일 수 있었으며, 대칭적인 배치는 판정 구조를 설명하기 쉽다. PAPR 우위는 열별 연산량이나 SER·BER 우위를 보장하지 않는다. PA 제약 시나리오에서 파형의 높은 백분위수는 필요한 피크 여유를 비교하는 근거가 된다. 허용 BER과 평균 송신전력 제한을 함께 적용한 최종 선택은 팀 데이터가 확보된 뒤 판단한다.

검증된 CSV와 그림은 [baseline 보존본](../analysis/baseline_results/rrc_sweep_verified/README.md)에 있다.
