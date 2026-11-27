"""Integrate validated A/B results with C's official mapped analysis."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
import numpy as np
import pandas as pd

from analysis.analyze import COLORS, MARKERS, SCHEMES, save
from analysis.validate_final_inputs import INPUTS, validate

KEYS = ["scheme", "ebn0_db"]
PRELIMINARY = Path("analysis/preliminary_results")
RECEIPT = Path("results/metrics/optimized_run_receipt.json")
THEORY = Path("results/metrics/theoretical_ser.csv")
COORDINATE_OUTPUTS = (
    "constellation_metrics.csv", "receiver_complexity.csv", "receiver_operation_counts.csv",
    "waveform_papr.csv", "waveform_papr_summary.csv",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_preliminary(output: Path) -> None:
    """Check all coordinate-only tables against the published preliminary run."""
    for name in COORDINATE_OUTPUTS:
        pd.testing.assert_frame_equal(
            pd.read_csv(output / name), pd.read_csv(PRELIMINARY / name), check_exact=True,
        )


def combine_simulation() -> pd.DataFrame:
    """Align paired AWGN observations and the theory by scheme and Eb/N0."""
    simulation = pd.read_csv("results/metrics/simulation_results.csv")
    initial = simulation[simulation.mapping.eq("initial")].drop(columns="mapping")
    optimized = simulation[simulation.mapping.eq("optimized")].drop(columns="mapping")
    paired = initial.merge(
        optimized, on=KEYS, suffixes=("_initial", "_optimized"), validate="one_to_one",
    )
    if len(paired) != len(initial) or len(paired) != len(optimized):
        raise ValueError("Initial and optimized runs must cover the same points.")
    for column in ("num_symbols", "num_bits", "seed", "symbol_errors", "SER"):
        pd.testing.assert_series_equal(
            paired.pop(f"{column}_initial"), paired[f"{column}_optimized"], check_names=False,
        )
        paired = paired.rename(columns={f"{column}_optimized": column})
    paired["BER_reduction_percent"] = 100 * (
        paired.BER_initial - paired.BER_optimized
    ) / paired.BER_initial.where(paired.BER_initial.gt(0))
    # For zero symbol errors, give the exact one-sided 95% binomial upper bound.
    paired["SER_zero_count_upper95"] = (-np.expm1(np.log(0.05) / paired.num_symbols)).where(
        paired.symbol_errors.eq(0)
    )
    theory = pd.read_csv(THEORY)
    comparison = paired.merge(theory, on=KEYS, validate="one_to_one")
    if len(comparison) != len(paired) or len(comparison) != len(theory):
        raise ValueError("A's theoretical SER must cover the same points as B's observations.")
    comparison["SER_minus_nearest_approx"] = comparison.SER - comparison.nearest_approx
    return comparison


def write_plots(comparison: pd.DataFrame, directory: Path) -> None:
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def plot(series: str, title: str, label_y: str, filename: str, overlay: str = "") -> None:
        fig, ax = plt.subplots(figsize=(8, 5))
        for scheme, color, marker in zip(SCHEMES, COLORS, MARKERS):
            data = comparison[comparison.scheme.eq(scheme)].sort_values("ebn0_db")
            x = data.ebn0_db
            ax.semilogy(x, data[series].where(data[series].gt(0)),
                        color=color, marker=marker, markersize=4, label=scheme)
            if overlay:
                ax.semilogy(x, data[overlay].where(data[overlay].gt(0)),
                            color=color, linestyle="--", alpha=0.7)
        ax.set(title=title, xlabel="Eb/N0 (dB)", ylabel=label_y, xticks=range(0, 21, 2))
        ax.legend(ncol=2)
        ax.grid(True, which="both", alpha=0.2)
        zero_note = "Zero-error samples omitted from log axis (see CSV)."
        if overlay:
            detail = ("Solid: optimized; dashed: initial."
                      if overlay == "BER_initial"
                      else "Solid: measured; dashed: nearest-pair SER approximation.")
            zero_note = detail + "\n" + zero_note
        fig.text(0.12, 0.01, zero_note, fontsize=8)
        fig.subplots_adjust(bottom=0.18)
        save(fig, directory / filename)

    plot("SER", "Official 32-QAM: measured SER", "SER", "official_ser")
    plot("BER_optimized", "Official 32-QAM: BER before and after mapping optimization",
         "BER", "official_ber_mapping", "BER_initial")
    plot("SER", "Official 32-QAM: measured and theoretical SER", "SER",
         "official_ser_theory", "nearest_approx")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="Output from analysis/analyze.py")
    args = parser.parse_args()
    output = args.out
    validate(Path.cwd(), RECEIPT)
    metadata_path = output / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (metadata["baseline"]
            or metadata.get("input_sha256") != sha256(Path("data/mapped_constellations.csv"))
            or metadata.get("reference_sha256") != sha256(Path("data/constellations.csv"))):
        raise ValueError("Expected an official mapped analysis from the current A/B inputs.")
    compare_preliminary(output)

    comparison = combine_simulation()
    if not (output / "figures").is_dir():
        raise ValueError("The mapped analyzer output must contain its figures directory.")
    comparison.to_csv(output / "paired_ser_ber.csv", index=False)

    metrics = pd.read_csv(output / "constellation_metrics.csv")
    receiver = pd.read_csv(output / "receiver_operation_counts.csv")
    receiver = receiver[receiver.case.eq("average")].drop(columns="case")
    preferred = receiver[receiver.receiver.eq("independent_iq") | (
        receiver.receiver.eq("grouped") & receiver.scheme.ne("Rectangular")
    )]
    waveform = pd.read_csv(output / "waveform_papr_summary.csv")
    waveform = waveform[waveform.roll_off.eq(0.35) & waveform.samples_per_symbol.eq(8)]
    final = (comparison.merge(metrics, on="scheme", validate="many_to_one")
             .merge(preferred, on="scheme", validate="many_to_one")
             .merge(waveform, on="scheme", validate="many_to_one"))
    final.to_csv(output / "final_comparison.csv", index=False)
    write_plots(comparison, output / "figures")
    metadata.update(
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        integration_scope="official optimized mapping; paired simulation for both mappings",
        integration_input_sha256={
            str(path): sha256(path) for path in [
                *map(Path, INPUTS), THEORY, RECEIPT,
                *(PRELIMINARY / name for name in COORDINATE_OUTPUTS),
                Path("analysis/analyze.py"), Path("analysis/integrate_final.py"),
            ]
        },
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(COORDINATE_OUTPUTS)} preliminary tables; integrated {len(final)} SNR rows.")


if __name__ == "__main__":
    main()
