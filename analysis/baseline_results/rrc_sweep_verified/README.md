# 검증된 baseline 산출물

교수님 제공 예제 성상도와 기준 비트 라벨을 사용한 결과다. 팀 최종 결과는 별도 실행 폴더에 저장한다.

- `constellation_metrics.csv`와 `receiver_complexity.csv`는 성상도 수치 및 ML 판정 검증 결과다.
- `receiver_operation_counts.csv`는 수신 심볼당 이론적 연산 수다.
- `waveform_papr_summary.csv`는 roll-off와 SPS를 바꾼 48개 조합의 평균 및 95·99백분위수다.
- `run_metadata.json`에는 기준 입력의 SHA-256과 시드, 필터 및 프레임 조건이 들어 있다.
- `figures/`에는 네 방식의 결정 영역과 PAPR·CCDF를 PNG 및 벡터 PDF로 보관했다. CCDF의 조건은 roll-off 0.35와 8 SPS다.

기본 조건의 프레임별 원본 CSV는 기존 로컬 실행 폴더에 있다. 전체 프레임 데이터 재생성 방법과 결과 해석은 [C 분석 문서](../../../docs/C_analysis.md)에 정리했다.
