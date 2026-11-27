# 디지털통신 10조 팀원 B 최종 검수 및 인계

A의 확정 좌표 `2a5d016`으로 생성한 B의 제출 산출물 `86b6cb0`을 검수했다. 최종 32-QAM 실험 대기 항목은 없다. Scenario 5는 링크 설계 초안이며, 실제 경보 패킷 실패확률과 종단 간 지연은 별도 검증 대상이다. [팀원 B 보고서 초안](B_report_draft.md)

## 인계표

| 자료 | 저장소 경로 | 용도 | 상태 |
| --- | --- | --- | --- |
| A 입력 | [data/constellations.csv](../data/constellations.csv), [geometry_metrics.csv](../results/metrics/geometry_metrics.csv), [theoretical_ser.csv](../results/metrics/theoretical_ser.csv) | 성상도별 32점의 좌표, 기하 지표, 이론 SER 근사와 경계 | 확정 · 전달 가능 |
| C++ 소스 및 빌드 | [rectangular_experiment.cpp](../simulation/LinkLevelSimulation/rectangular_experiment.cpp), [CMakeLists.txt](../simulation/LinkLevelSimulation/CMakeLists.txt), [professor-adaptation.patch](../simulation/LinkLevelSimulation/professor-adaptation.patch) | 매핑 CSV 입력, AWGN, 최소거리 복조, 오류 집계. 빌드에 교수님 원본 `Source` 필요 | Windows 재빌드 확인 · 전달 가능 |
| Python 코드 | [mapping_optimizer.py](../simulation/mapping_optimizer.py), [run_experiment.py](../simulation/run_experiment.py), [experiment_comparison.py](../simulation/experiment_comparison.py) | 매핑 최적화, C++ 실행, 결과 검증, 그래프 및 보간 | 재실행 확인 · 전달 가능 |
| 매핑 좌표 CSV | [data/mapped_constellations.csv](../data/mapped_constellations.csv) | A 원래 좌표와 `point_id`에 최적화 5비트 라벨 추가 | 128행 · 전달 가능 |
| 매핑 지표 CSV | [results/metrics/mapping_metrics.csv](../results/metrics/mapping_metrics.csv) | 초기·최적화 평균 인접 해밍 거리와 Gray edge 비율 | 8행 · 전달 가능 |
| 실험 결과 CSV | [results/metrics/simulation_results.csv](../results/metrics/simulation_results.csv) | 4종 × 21개 SNR × 2개 매핑의 전송·오류 수와 SER·BER | 168행 · 전달 가능 |
| 해시 기록 | [results/metrics/optimized_run_receipt.json](../results/metrics/optimized_run_receipt.json) | C 최종 분석에 입력과 산출물의 버전 일치 확인 | C 입력 검사 통과 · 전달 가능 |
| SER 및 BER 그래프 | SER [PNG](../results/figures/ser_comparison.png) · [PDF](../results/figures/ser_comparison.pdf), BER [PNG](../results/figures/ber_comparison.png) · [PDF](../results/figures/ber_comparison.pdf) | 4종 비교, 초기·최적화 BER과 관측 오류 0회 표시 | 전달 가능 |
| 이론 SER 비교 | [PNG](../results/figures/ser_theory_comparison.png) · [PDF](../results/figures/ser_theory_comparison.pdf) | 최근접 근사, 쌍별 하계, 합집합 상계와 관측 SER | 전달 가능 |
| 보고서 초안 | [docs/B_report_draft.md](B_report_draft.md) | B 담당 절과 Scenario 5 복붙용 원고 | 초안 전달 가능 |
| 실제 Alarm 성능 | [보고서의 Scenario 5](B_report_draft.md#10-scenario-5-산업용-긴급-alarm) | 패킷 실패확률과 종단 간 지연을 실제 프레임 단위로 비교 | 패킷 수준 실험 대기 |

## 최종 검수 결과

- 현재 A의 좌표·기하 지표·이론 SER은 인계 커밋 `2a5d016`의 파일과 바이트 단위로 일치한다. 최적화 매핑의 좌표와 `point_id` 128행은 A의 원본과 일치하고, 각 성상도에 5비트 라벨 32개가 한 번씩 있다.
- 결과 168행에서 `SER = symbol_errors / num_symbols`, `BER = bit_errors / num_bits`를 재계산했으며 `num_bits = 5 × num_symbols`임을 확인했다. 같은 성상도·SNR의 84쌍에서 시드, 전송 심볼 수, 심볼 오류 수가 일치했다.
- B 보고서의 10 dB SER·BER 표, 매핑 예시, 목표 오류율 $10^{-3}$ 보간값을 CSV와 대조했다. SER·BER 그래프의 x축은 `Eb/N0 (dB)`, y축은 로그 오류율이다. 양의 오류율을 본 곡선에서 확인하고, 오류 0회는 하단 패널의 해당 SNR에 표시한다. Type1~3은 18~20 dB, Rectangular는 19~20 dB이다. 이론 SER 비교 그림의 ×는 같은 SNR의 오류 0회 표시이며 위치의 세로값에 확률 의미를 부여하지 않는다.
- 깨끗한 교수님 원본 복사본으로 Windows x64, MSVC 19.44.35217.0 Release에서 재빌드했다. Python 3.13.12와 Matplotlib 3.11.2에서 재실행한 CSV 3종, SHA-256 기록, 그래프 PNG·PDF 6개가 제출본과 모두 바이트 단위로 일치했다. C의 최종 입력 검사도 통과했다.
- 2단계 재현 문서가 제출용 CSV를 덮어쓸 수 있어 출력 경로를 `build/rectangular/baseline.csv`로 바꿨다. 2단계 기록은 당시 기준 CSV 커밋을 가리키도록 고쳤다. 보고서 명령은 A의 Git 원본 LF 파일로 입력을 준비하도록 정리했다.

## 확인한 Windows 재실행 명령

팀 저장소와 교수님 제공 `LinkLevelSimulation` 폴더가 나란히 있는 상태에서 실행한다. 아래는 새 `build/stage7-audit` 폴더 기준이다. Python 환경에 `python -m pip install -r requirements.txt`로 의존성을 설치하고, Visual Studio 2022의 C++ 도구와 CMake를 준비한다. [기존 빌드 안내와 macOS 명령](../simulation/README.md)

~~~powershell
New-Item -ItemType Directory -Force build/stage7-audit/professor | Out-Null
Copy-Item -LiteralPath ../LinkLevelSimulation/Source -Destination build/stage7-audit/professor -Recurse
git apply --ignore-space-change --directory=build/stage7-audit/professor simulation/LinkLevelSimulation/professor-adaptation.patch
cmake -S simulation/LinkLevelSimulation -B build/stage7-audit/bin -G 'Visual Studio 17 2022' -A x64 "-DPROFESSOR_SOURCE_DIR=$PWD/build/stage7-audit/professor/Source"
cmake --build build/stage7-audit/bin --config Release
python -c "from pathlib import Path; from subprocess import check_output; root=Path('build/stage7-audit/input'); files=('data/constellations.csv','results/metrics/theoretical_ser.csv'); [(root/name).parent.mkdir(parents=True,exist_ok=True) or (root/name).write_bytes(check_output(['git','show','2a5d016:'+name])) for name in files]"
python simulation/run_experiment.py --constellations build/stage7-audit/input/data/constellations.csv --theoretical-ser build/stage7-audit/input/results/metrics/theoretical_ser.csv --simulator build/stage7-audit/bin/Release/rectangular_experiment.exe --output-root build/stage7-audit/output --max-symbols 2000000 --target-errors 2000 --seed 20261128 --receipt
~~~

## 발표 질문

**같은 성상도에서 매핑을 바꾸면 왜 SER은 같고 BER은 달라질 수 있는가?**

같은 좌표에서 같은 잡음을 받으면 최소거리 수신기가 고르는 점이 같으므로 심볼 오류 발생 여부가 같다. 그 두 점의 비트 라벨을 바꾸면 해밍 거리가 달라져 같은 오판도 비트 오류 개수가 달라진다.

**원본의 Es/N0를 팀 실험의 Eb/N0로 어떻게 바꿨는가?**

비부호화 32-QAM은 심볼당 5비트이므로 $E_s/N_0=5(E_b/N_0)$이며, dB에서는 원본 기준인 $E_s/N_0$가 $E_b/N_0$보다 약 6.99 dB 높다. 팀의 입력은 $E_b/N_0$로 두고, $E_s=1$에서 I/Q 각각에 분산 $1/(10\cdot10^{(E_b/N_0)_{\mathrm{dB}}/10})$을 적용했다.

**긴급 Alarm에서 어떤 변조를 선택했고, 무엇을 얻고 무엇을 포기했는가?**

기한 안에 경보를 정확히 전달하기 위해 Gray QPSK를 기본안으로 선정했다. 같은 $E_b/N_0$의 이상적 AWGN에서 BPSK와 같은 이론 BER을 가지며 같은 심볼률에서 BPSK보다 두 배의 비트를 보내지만, 32-QAM 대비 명목 비트율은 40%이다.
