# 공식 매핑 최종 분석

입력은 A의 공식 4종 성상도와 B의 최적화 Mapping 및 검증된 AWGN 실험이다. C의 baseline과 좌표 전용 preliminary 결과는 각 원래 경로에 보존했다.

- `final_comparison.csv`는 4종 × 21 Eb/N0에서 공식 SER·BER, PAPR, 연산량, 대칭 지표를 결합한다. 수신기 열은 Rectangular 독립 I/Q와 Type1~3 그룹 ML의 심볼당 연산이다.
- `paired_ser_ber.csv`는 같은 난수 표본의 초기·최적화 BER, 공통 SER·오류 수, A의 이론 SER 및 차이를 기록한다. 오류 0회인 점은 SER의 단측 95% 상한을 별도 열에 기록한다.
- 나머지 CSV 5개는 성상도 지표, 수신기 판정 검증, 연산 수, 기본 RRC 조건의 프레임별 PAPR, RRC sweep 48개 조합 요약이다. 이 결과는 preliminary 5개 표와 일치한다.
- `figures/`에는 심볼 ML 결정 영역 4종, 최적화 Mapping의 비트 결정 영역 4종, 성상점 PAPR, 파형 CCDF, 공식 SER, 초기·최적화 BER, 이론·실험 SER 비교를 PNG와 PDF로 저장했다.
- `run_metadata.json`에는 Git 커밋, 입력·코드 SHA-256, 시드와 RRC 조건을 기록했다.

저장소 루트와 설치된 가상환경에서 재현한다. 출력에는 새 경로를 지정한다.

```sh
python -m analysis.validate_final_inputs --receipt results/metrics/optimized_run_receipt.json &&
python analysis/analyze.py --input data/mapped_constellations.csv --reference data/constellations.csv --out analysis_runs/final_optimized --waveform-sweep &&
python -m analysis.integrate_final --out analysis_runs/final_optimized
python -m unittest analysis.test_analyze -v
```

[최종 보고서](../../docs/C_analysis.md)

## 재현 검증

커밋 `1531935`의 팀 입력으로 새 임시 폴더에 다시 실행했다. CSV 7개와 메타데이터는 바이트 단위, PNG 13개는 픽셀 단위, PDF 13개는 생성 시각을 제외하고 바이트 단위로 일치했다. 공식 최소거리 간선에서 초기·최적화 라벨의 평균 해밍 거리와 Gray edge 비율을 재계산해 B 지표 8행을 확인했다. 네 방식의 ML 다각형 꼭짓점도 각 소속 심볼의 최소거리 조건을 만족했다. 단위 테스트 9개와 `git diff --check`를 통과했다.
