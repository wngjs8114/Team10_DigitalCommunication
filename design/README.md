# 성상도 설계

프로젝트 루트에서 requirements.txt의 패키지를 설치한 뒤 실행한다.

```sh
python design/constellation_search.py --candidates-only
python design/constellation_search.py --rectangular reference/rectangular.csv
```

첫 명령은 Type1~3의 좌표, 거리 분포, 이론적 SER과 그림을 design/candidates/에 저장한다. 두 번째 명령에 사용하는 기준 CSV는 헤더가 I_raw,Q_raw이며 교수님이 제공한 32개 정수 좌표를 원래 순서대로 적는다. 완전한 4종 결과는 data/constellations.csv와 results/에 생성한다. --output-root로 별도 출력 위치를 지정할 수 있다. B와 C가 Mapping과 분석을 시작한 뒤에는 확정 좌표 및 point_id를 유지한다.

[설계 방법과 후보 결과](../docs/A_design.md)
