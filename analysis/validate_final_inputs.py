"""Check the evidence required before running the final C analysis."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.analyze import SCHEMES, load, validate_mapping

CONSTELLATIONS = "data/constellations.csv"
MAPPED = "data/mapped_constellations.csv"
GEOMETRY = "results/metrics/geometry_metrics.csv"
SIMULATION = "results/metrics/simulation_results.csv"
MAPPING = "results/metrics/mapping_metrics.csv"
INPUTS = (CONSTELLATIONS, MAPPED, GEOMETRY, SIMULATION, MAPPING)


def read_metrics(path: Path, columns: str) -> pd.DataFrame:
    """Reject malformed headers and missing or non-finite numeric values."""
    frame = pd.read_csv(path)
    if frame.columns.tolist() != columns.split(",") or not isinstance(frame.index, pd.RangeIndex):
        raise ValueError(f"{path}: unexpected CSV structure.")
    if frame.empty or not set(frame.scheme).issubset(SCHEMES):
        raise ValueError(f"{path}: missing data or unknown scheme.")
    for column in frame.columns.difference(["scheme", "mapping"]):
        frame[column] = pd.to_numeric(frame[column])
        if not np.isfinite(frame[column]).all():
            raise ValueError(f"{path}: missing or non-finite values in {column}.")
    return frame


def validate(root: Path, receipt: Path) -> None:
    paths = {name: root / name for name in INPUTS}
    missing = [str(path) for path in [*paths.values(), receipt] if not path.is_file()]
    if missing:
        raise ValueError("Missing final inputs: " + ", ".join(missing))

    # The receipt must come from the simulator run, before replacing any input.
    expected = json.loads(receipt.read_text(encoding="utf-8"))
    if not isinstance(expected, dict):
        raise ValueError("Expected a JSON object with version hashes.")
    for name in (CONSTELLATIONS, MAPPED, SIMULATION, MAPPING):
        actual = hashlib.sha256(paths[name].read_bytes()).hexdigest()
        if actual != expected.get(name):
            raise ValueError(f"{name}: SHA-256 differs from B's optimized-run receipt.")

    reference, mapped = load(paths[CONSTELLATIONS]), load(paths[MAPPED])
    if "bit_label" in reference or "bit_label" not in mapped:
        raise ValueError("Expected unmapped A coordinates and mapped B coordinates.")
    validate_mapping(mapped, reference)

    geometry = read_metrics(
        paths[GEOMETRY], "scheme,Es_raw,normalization_factor,d_min,mean_nearest_neighbors",
    )
    if sorted(geometry.scheme) != sorted(SCHEMES):
        raise ValueError("Geometry metrics must contain one row per scheme.")
    for name, group in reference.groupby("scheme"):
        raw = group[["I_raw", "Q_raw"]].to_numpy()
        points = group[["I_norm", "Q_norm"]].to_numpy()
        energy = np.mean(np.sum(raw**2, axis=1))
        distances = np.linalg.norm(points[:, None] - points[None, :], axis=2)
        np.fill_diagonal(distances, np.inf)
        expected_values = [energy, 1 / np.sqrt(energy), distances.min()]
        actual_values = geometry.set_index("scheme").loc[
            name, ["Es_raw", "normalization_factor", "d_min"]
        ].to_numpy(dtype=float)
        if not np.allclose(actual_values, expected_values, rtol=0, atol=1e-6):
            raise ValueError(f"{name}: geometry metrics disagree with A's coordinates.")

    mapping = read_metrics(paths[MAPPING], "scheme,mapping,mean_neighbor_hamming,gray_edge_ratio")
    sim = read_metrics(
        paths[SIMULATION],
        "scheme,mapping,ebn0_db,num_symbols,num_bits,symbol_errors,bit_errors,SER,BER,seed",
    )
    for frame in (mapping, sim):
        if not set(frame.mapping).issubset({"initial", "optimized"}):
            raise ValueError("Unknown mapping label.")
        if set(frame.loc[frame.mapping == "optimized", "scheme"]) != set(SCHEMES):
            raise ValueError("Optimized results are required for all four schemes.")
    if (mapping.duplicated(["scheme", "mapping"]).any()
            or not mapping.gray_edge_ratio.between(0, 1).all()
            or not mapping.mean_neighbor_hamming.between(1, 5).all()):
        raise ValueError("Mapping metrics contain duplicate keys or invalid values.")

    counts = sim[["num_symbols", "num_bits", "symbol_errors", "bit_errors"]].to_numpy()
    num_symbols, num_bits, symbol_errors, bit_errors = counts.T
    if (np.any(counts < 0) or np.any(counts != np.floor(counts))
            or np.any(num_symbols == 0) or np.any(num_bits != 5 * num_symbols)
            or np.any(symbol_errors > num_symbols) or np.any(bit_errors > num_bits)
            or np.any(bit_errors < symbol_errors) or np.any(bit_errors > 5 * symbol_errors)):
        raise ValueError("SER/BER denominators or error counts are inconsistent.")
    for rate, observed in (("SER", symbol_errors / num_symbols), ("BER", bit_errors / num_bits)):
        if not sim[rate].between(0, 1).all() or not np.allclose(
            sim[rate], observed, rtol=1e-6, atol=0
        ):
            raise ValueError(f"{rate} must match the corresponding error and trial counts.")
    optimized = sim[sim.mapping == "optimized"]
    grids = optimized.groupby("scheme").ebn0_db.agg(set)
    if any(grid != set(range(21)) for grid in grids):
        raise ValueError("Optimized SER/BER must cover the shared 0–20 dB grid.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True, help="B's optimized-run SHA-256 receipt")
    args = parser.parse_args()
    try:
        validate(Path.cwd(), args.receipt)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("Final input checks passed. Compare optimized SER and BER separately.")


if __name__ == "__main__":
    main()
