# 공식 좌표 중간 분석

A의 공식 성상도 4종을 사용한 C 분석이다. B의 최종 비트 라벨이 전달되면 BER 결정 영역을 계산한다. 기존 baseline은 `analysis/baseline_results/rrc_sweep_verified/`에 있다.

- 성상도와 검산 · `constellation_metrics.csv`, `geometry_audit.csv`
- 수신기 · `receiver_complexity.csv`, `receiver_operation_counts.csv`
- 파형 · `waveform_papr.csv` (기본 조건의 프레임별 값), `waveform_papr_summary.csv` (48개 조합), `waveform_baseline_comparison.csv` (공식−baseline 차이)
- 기하 비교 · `boundary_geometry_comparison.csv` (표시 창 ±2 내의 내부 결정 선분과 사선 수)
- 그림 · `figures/`의 4종 심볼 ML 경계, 심볼 PAPR, 기본 조건의 파형 CCDF를 각각 PNG와 PDF로 보존
- 재현성 · `run_metadata.json`의 Git commit, 분석 코드 버전, 입력 해시, 시드 및 RRC 조건

재실행할 때는 새 출력 경로를 사용한다.

```sh
python analysis/analyze.py --input data/constellations.csv --out analysis_runs/official_coordinates --waveform-sweep
```

검산 정의, 이론 SER 분석, B의 Rectangular 초기 검증은 [C 분석 문서](../../docs/C_analysis.md)에 정리했다.
