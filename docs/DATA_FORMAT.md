# 공통 CSV 규격

모든 CSV는 UTF-8, 쉼표 구분, 헤더 포함 형식이다. 아래 열 이름, 순서, 정의를 유지하며 공통 규격은 팀 합의 없이 변경하지 않는다. `scheme`은 [공통 실험 규격](EXPERIMENT_PROTOCOL.md)의 명칭을 사용한다.

## `data/constellations.csv`

```csv
scheme,point_id,I_raw,Q_raw,I_norm,Q_norm
```

- 각 방식의 `point_id`는 0~31이며, 비트 Mapping과 독립적인 성상점 식별자다. 데이터는 총 128행이다.
- `I_raw`, `Q_raw`는 원본 좌표이고 `I_norm`, `Q_norm`은 평균 심볼 에너지를 1로 정규화한 좌표다.
- 성상점 확정 후 `point_id`와 좌표의 대응을 임의로 바꾸지 않는다.

## `data/mapped_constellations.csv`

```csv
scheme,point_id,I_raw,Q_raw,I_norm,Q_norm,bit_label
```

- `constellations.csv`의 `point_id`와 좌표를 보존한다.
- `bit_label`은 `00000`~`11111`의 5자리 문자열이다. 읽고 쓸 때 선행 0을 보존하고 각 방식에 모든 비트 문자열을 정확히 한 번씩 사용한다.

## `results/metrics/geometry_metrics.csv`

```csv
scheme,Es_raw,normalization_factor,d_min,mean_nearest_neighbors
```

`Es_raw`는 원본 좌표의 평균 심볼 에너지, `normalization_factor`는 좌표에 곱하는 정규화 계수다. `d_min`은 정규화 성상도의 최소 점간 거리이며 `mean_nearest_neighbors`는 최근접 이웃 수의 평균이다.

## `results/metrics/simulation_results.csv`

```csv
scheme,mapping,ebn0_db,num_symbols,num_bits,symbol_errors,bit_errors,SER,BER,seed
```

- `mapping`은 `initial` 또는 `optimized`다. `ebn0_db`는 Eb/N0의 dB 값이고 `seed`는 난수 시드다.
- `num_bits = 5 × num_symbols`로 계산한다. `symbol_errors`와 `bit_errors`는 실제 관측 오류 수다.
- `SER`과 `BER`은 각각 심볼 오류 수와 비트 오류 수를 해당 총수로 나눈 0~1 범위의 관측 비율이다.

## `results/metrics/mapping_metrics.csv`

```csv
scheme,mapping,mean_neighbor_hamming,gray_edge_ratio
```

`mapping`은 `initial` 또는 `optimized`다. `mean_neighbor_hamming`은 이웃 간 비트 라벨의 평균 해밍 거리, `gray_edge_ratio`는 해밍 거리가 1인 이웃 간 연결의 비율이다. 비교 시 사용한 이웃 판정 기준을 기록한다.

## `results/metrics/constellation_metrics.csv`

```csv
scheme,Es_norm,d_min,papr_linear,papr_db,mean_I,mean_Q,energy_I,energy_Q,cov_IQ,sym_origin,sym_I,sym_Q,sym_rot90
```

- `Es_norm`과 `d_min`은 정규화 성상도의 평균 심볼 에너지와 최소 점간 거리다.
- `papr_linear`는 최대 심볼 에너지를 평균 심볼 에너지로 나눈 값이며 `papr_db = 10log10(papr_linear)`이다.
- `mean_I`, `mean_Q`는 각 축 좌표의 평균이고 `energy_I`, `energy_Q`는 각각 좌표 제곱의 평균이다. `cov_IQ`는 모집단 공분산이다.
- 대칭성은 성립 시 1, 그 외에는 0으로 기록한다. `sym_origin`은 원점 대칭, `sym_I`는 I축 반사 대칭, `sym_Q`는 Q축 반사 대칭, `sym_rot90`은 원점 기준 90° 회전 대칭이다.
