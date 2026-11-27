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
.\build\rectangular\Release\rectangular_experiment.exe results/metrics/simulation_results.csv 2000000 2000
.\build\rectangular\Release\rectangular_experiment.exe build/rectangular/repeat.csv 2000000 2000
Get-FileHash results/metrics/simulation_results.csv,build/rectangular/repeat.csv
~~~

### macOS

~~~sh
mkdir -p build/professor
cp -R ../LinkLevelSimulation/Source build/professor/
git apply --ignore-space-change --directory=build/professor simulation/LinkLevelSimulation/professor-adaptation.patch
cmake -S simulation/LinkLevelSimulation -B build/rectangular -DCMAKE_BUILD_TYPE=Release -DPROFESSOR_SOURCE_DIR="$PWD/build/professor/Source"
cmake --build build/rectangular
./build/rectangular/rectangular_experiment results/metrics/simulation_results.csv 2000000 2000
~~~

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
