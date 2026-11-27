# Mapping 및 시뮬레이션

교수님 제공 LinkLevelSimulation 프로젝트의 `Source` 디렉터리를 준비한다. 실험은 원본 `QAM32(0)`의 좌표와 라벨 순서, 변조, 최소거리 복조, 오류 집계를 재사용한다. 실험 조건과 결과는 [B 실험 기록](../docs/B_simulation.md)에 있다.

프로젝트 루트에서 아래 명령을 실행한다. 예시는 원본 폴더와 팀 저장소가 나란히 있을 때의 경로이다. 패치는 깨끗한 원본 복사본에 한 번 적용한다.

### Windows PowerShell

~~~powershell
New-Item -ItemType Directory -Force build/professor | Out-Null
Copy-Item -LiteralPath ../LinkLevelSimulation/Source -Destination build/professor -Recurse
git apply --ignore-space-change --directory=build/professor simulation/LinkLevelSimulation/professor-adaptation.patch
cmake -S simulation/LinkLevelSimulation -B build/rectangular -G 'Visual Studio 17 2022' -A x64 "-DPROFESSOR_SOURCE_DIR=$PWD/build/professor/Source"
cmake --build build/rectangular --config Release
.\build\rectangular\Release\rectangular_experiment.exe build/rectangular/smoke.csv 1000 2000
.\build\rectangular\Release\rectangular_experiment.exe build/rectangular/baseline.csv 2000000 2000
.\build\rectangular\Release\rectangular_experiment.exe build/rectangular/repeat.csv 2000000 2000
Get-FileHash build/rectangular/baseline.csv,build/rectangular/repeat.csv
~~~

### macOS

~~~sh
mkdir -p build/professor
cp -R ../LinkLevelSimulation/Source build/professor/
git apply --ignore-space-change --directory=build/professor simulation/LinkLevelSimulation/professor-adaptation.patch
cmake -S simulation/LinkLevelSimulation -B build/rectangular -DCMAKE_BUILD_TYPE=Release -DPROFESSOR_SOURCE_DIR="$PWD/build/professor/Source"
cmake --build build/rectangular
./build/rectangular/rectangular_experiment build/rectangular/baseline.csv 2000000 2000
~~~

위 단독 실험은 내장 Rectangular 기준을 재현한다. 제출용 4종 실험은 아래 일괄 실행 절차를 사용한다.

인자 순서는 출력 CSV, 지점당 최대 전송 심볼 수, 목표 심볼 오류 수이다. 두 수를 생략하면 각각 2,000,000과 2,000을 사용한다. 같은 빌드에서 같은 인자로 실행하면 같은 결과를 얻는다. C++ 표준 라이브러리 구현에 따라 정규 난수열은 달라질 수 있다.


## Gray-like 매핑

프로젝트 루트에서 실행한다. Python 3.10 이상을 사용하며 매핑과 짧은 AWGN 비교는 표준 라이브러리로 실행한다.

~~~sh
python simulation/mapping_optimizer.py --qam32-source ../LinkLevelSimulation/Source/Modulation/QAMa/QAM32.cpp --mapped-output simulation/builtin/data/mapped_constellations.csv --metrics-output simulation/builtin/results/metrics/mapping_metrics.csv --seed 20261128 --smoke-type Type3
~~~

내장 성상도 결과는 `simulation/builtin/` 아래에 있다. `mapped_constellations.csv`는 최적화 라벨을 저장한다. 초기 라벨은 `point_id`를 5자리 이진수로 변환하면 복원할 수 있다. `mapping_metrics.csv`에는 두 매핑의 지표가 있으며 목적함수와 Gray edge 개수는 실행 시 출력된다. `--smoke-type`을 지정하면 두 매핑에 같은 Type의 송신점과 잡음을 적용해 10 dB에서 50,000심볼을 비교한다. [수식 및 관측 결과](../docs/B_simulation.md#3단계--내장-성상도-gray-like-매핑)

A 좌표의 보존 여부를 확인하는 명령은 아래와 같다. 이 예시는 저장소의 `build/` 아래에 출력한다.

~~~sh
python simulation/mapping_optimizer.py --constellations data/constellations.csv --mapped-output build/mapping-stage3/mapped_constellations.csv --metrics-output build/mapping-stage3/mapping_metrics.csv --seed 20261128
~~~


## 매핑·C++ 시뮬레이션·그래프 일괄 실행

위 절차대로 `rectangular_experiment`를 빌드하고, Python 환경에 `python -m pip install -r requirements.txt`로 그래프 의존성을 설치한다. 다음 예시는 Windows PowerShell에서 저장소 루트를 기준으로 실행한다. macOS에서는 `--simulator build/rectangular/rectangular_experiment`를 사용한다.

### 내장 좌표로 통합 검증

~~~powershell
python simulation/run_experiment.py --builtin-qam32 ../LinkLevelSimulation/Source/Modulation/QAMa/QAM32.cpp --simulator build/rectangular/Release/rectangular_experiment.exe --output-root simulation/builtin/validation --levels "0,6,12" --max-symbols 100000 --target-errors 2000 --seed 20261128
~~~

원본 배열을 팀 CSV 규격의 `data/builtin_constellations.csv`로 내보낸 뒤 같은 CSV 경로로 매핑과 C++ 실험을 실행한다. 출력은 지정한 루트 아래 `data/mapped_constellations.csv`, `results/metrics/mapping_metrics.csv`, `results/metrics/simulation_results.csv` 및 `results/figures/`에 기록한다. 내장 좌표 결과와 그래프에는 검증용 출처를 표시했다.

### A 확정 CSV로 전체 21개 지점 실행

~~~powershell
python simulation/run_experiment.py --constellations data/constellations.csv --simulator build/rectangular/Release/rectangular_experiment.exe --output-root build/final-awgn --max-symbols 2000000 --target-errors 2000 --seed 20261128
~~~

`--levels`를 생략하면 0~20 dB를 1 dB 간격으로 실행한다. 초기 라벨은 5비트 `point_id`이고 최적화 라벨은 매핑 CSV의 `bit_label`이다. 각 성상도·Eb/N0 지점에서 한 번 복조하고 두 라벨로 각각 비트 오류를 계산한다. SER 그래프에는 공통 곡선을 한 번만 그리고 BER 그래프는 초기 매핑을 점선, 최적화 매핑을 실선으로 표시한다. 관측 오류 0회 지점은 CSV에 0으로 기록하고 로그 그래프에 안내한다.


### 제출용 이론 비교와 SHA-256 기록

C에게 전달할 해시 기록이 필요하면 `--receipt`를 사용한다. 0~20 dB 전체 실행이 성공하면 `results/metrics/optimized_run_receipt.json`을 출력한다. `--theoretical-ser`를 사용하면 A의 최근접 근사와 쌍별 하계·합집합 상계를 실험 SER에 겹쳐 그린다.

아래 명령은 A가 전달한 `2a5d016`의 Git 원본 바이트(LF)로 이번 제출용 실험을 재현한다. 첫 줄은 원본 두 CSV를 `build/` 아래에 복사한다. Windows에서 Git의 CRLF 변환이 적용된 작업 사본도 좌표 수치가 같지만, 파일 바이트에 대한 SHA-256은 달라진다.

~~~powershell
python -c "from pathlib import Path; from subprocess import check_output; root=Path('build/stage5-input'); files=('data/constellations.csv','results/metrics/theoretical_ser.csv'); [(root/name).parent.mkdir(parents=True,exist_ok=True) or (root/name).write_bytes(check_output(['git','show','2a5d016:'+name])) for name in files]"
python simulation/run_experiment.py --constellations build/stage5-input/data/constellations.csv --theoretical-ser build/stage5-input/results/metrics/theoretical_ser.csv --simulator build/rectangular/Release/rectangular_experiment.exe --output-root build/stage5-final --receipt
~~~

명령은 초기·최적화의 목표 오류율별 Eb/N0 차이와 Rectangular 대비 차이를 출력한다. 목표값을 양의 실측 오류율로 양쪽에서 끼울 때만 로그 오류율에서 보간한다. 실측점이 목표값과 일치하면 그 지점의 Eb/N0를 사용한다. 0회 관측 지점을 포함한 구간과 여러 교차 후보가 있는 경우는 보간값을 출력하지 않는다.

C 검사기에 직접 전달할 때는 해시 대상인 좌표, 매핑, 매핑 지표, 실험 CSV 네 파일의 LF 원본 바이트를 유지한다. 새 Windows 체크아웃은 `git -c core.autocrlf=false clone <repository>`로 만들거나 위 명령의 재실행 산출물을 사용할 수 있다.
