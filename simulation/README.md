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
