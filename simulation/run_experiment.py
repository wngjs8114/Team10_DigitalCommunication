"""Run constellation CSVs through Gray-like mapping, C++ simulation, and plotting."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from experiment_comparison import THEORY_STYLES, read_theory, report_targets
from mapping_optimizer import (
    BITS, DEFAULT_SEED, POINT_FIELDS, SCHEMES, read_builtin, validate, write_csv,
)


RESULT_FIELDS = (
    "scheme", "mapping", "ebn0_db", "num_symbols", "num_bits",
    "symbol_errors", "bit_errors", "SER", "BER", "seed",
)
SCHEME_STYLES = dict(zip(
    SCHEMES, (("#64748B", "o"), ("#2563EB", "s"), ("#0D9488", "^"), ("#9333EA", "D")),
))
MAPPING_STYLES = {"initial": "--", "optimized": "-"}


def read_results(
    path: Path, levels: list[int], max_symbols: int, target_errors: int, seed: int,
) -> dict[tuple[str, int, str], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != RESULT_FIELDS:
            raise ValueError("Unexpected simulation results header")
        rows = list(reader)
    results = {(r["scheme"], int(r["ebn0_db"]), r["mapping"]): r for r in rows}
    expected = {
        (scheme, level, mapping)
        for scheme in SCHEMES for level in levels for mapping in MAPPING_STYLES
    }
    if len(rows) != len(expected) or set(results) != expected:
        raise ValueError("Expected exactly one result for each scheme, Eb/N0 and mapping")
    for scheme, level, mapping in sorted(expected):
        row = results[scheme, level, mapping]
        count = int(row["num_symbols"])
        bits = int(row["num_bits"])
        symbol_errors = int(row["symbol_errors"])
        bit_errors = int(row["bit_errors"])
        if not (
            1 <= count <= max_symbols and bits == BITS * count
            and 0 <= symbol_errors <= min(count, target_errors)
            and (count == max_symbols or symbol_errors == target_errors)
            and symbol_errors <= bit_errors <= BITS * symbol_errors
            and float(row["SER"]) == symbol_errors / count
            and float(row["BER"]) == bit_errors / bits
            and int(row["seed"]) == seed + level
        ):
            raise ValueError(f"Invalid counts or rates for {scheme}, {level} dB, {mapping}")
        paired = results[scheme, level, "initial"]
        if any(row[key] != paired[key] for key in ("num_symbols", "symbol_errors", "seed")):
            raise ValueError(f"Mappings did not share symbol outcomes for {scheme}, {level} dB")
    return results


def plot_results(
    results: dict[tuple[str, int, str], dict[str, str]],
    levels: list[int],
    directory: Path,
    builtin: bool,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for metric in ("SER", "BER"):
        zero_levels = {
            scheme: [level for level in levels if float(results[scheme, level, "optimized"][metric]) == 0]
            for scheme in SCHEMES
        }
        has_zeros = any(zero_levels.values())
        if has_zeros:
            fig, (ax, zero_ax) = plt.subplots(
                2, 1, figsize=(8.4, 6), facecolor="white", layout="constrained",
                sharex=True, gridspec_kw={"height_ratios": (4, 1)},
            )
            for row, (scheme, (color, marker)) in enumerate(SCHEME_STYLES.items()):
                xs = zero_levels[scheme]
                zero_ax.scatter(xs, [row] * len(xs), color=color, marker=marker, s=20)
            zero_ax.set_yticks(range(len(SCHEMES)), SCHEMES, fontsize=7)
            zero_ax.invert_yaxis()
            zero_ax.set_title("Zero observed errors (both mappings)", loc="left", fontsize=9)
            zero_ax.set_xlabel("Eb/N0 (dB)")
            zero_ax.grid(axis="x", alpha=0.3)
        else:
            fig, ax = plt.subplots(figsize=(8.4, 5), facecolor="white", layout="constrained")
            ax.set_xlabel("Eb/N0 (dB)")
        ax.set_yscale("log")
        positives = 0
        for scheme, (color, marker) in SCHEME_STYLES.items():
            # Both mapping rows have the same observed SER. Plot the shared series once.
            mappings = ("optimized",) if metric == "SER" else tuple(MAPPING_STYLES)
            for mapping in mappings:
                values = [float(results[scheme, level, mapping][metric]) for level in levels]
                positives += sum(value > 0 for value in values)
                ax.plot(
                    levels, [value if value > 0 else math.nan for value in values],
                    linestyle=MAPPING_STYLES[mapping], marker=marker, color=color,
                    markersize=5, linewidth=1.55,
                )
        if not positives:
            ax.set_ylim(1e-8, 1)
        handles = [
            Line2D([], [], color=color, marker=marker, label=scheme, linestyle="none")
            for scheme, (color, marker) in SCHEME_STYLES.items()
        ]
        if metric == "BER":
            handles += [
                Line2D([], [], color="#1f2937", linestyle=style, label=mapping.capitalize())
                for mapping, style in MAPPING_STYLES.items()
            ]
        ax.legend(handles=handles, ncols=2, fontsize=8)
        ax.set_ylabel(f"{metric} (probability)")
        ax.set_xticks(levels if len(levels) <= 7 else levels[::2])
        ax.grid(True, which="major", alpha=0.3)
        title = f"32-QAM {metric} · Built-in validation" if builtin else f"32-QAM {metric}"
        if metric == "SER":
            title += " · Shared by both mappings"
        ax.set_title(title)
        save_figure(fig, directory / f"{metric.lower()}_comparison")


def save_figure(fig, filename: Path) -> None:
    fig.savefig(filename.with_suffix(".png"), dpi=300, facecolor="white")
    fig.savefig(
        filename.with_suffix(".pdf"), facecolor="white",
        metadata={"CreationDate": None, "ModDate": None},
    )
    plt.close(fig)


def plot_theory(
    results: dict[tuple[str, int, str], dict[str, str]],
    theory: dict[tuple[str, int], dict[str, float]],
    levels: list[int],
    directory: Path,
) -> None:
    fig, axes = plt.subplots(
        2, 2, figsize=(9.2, 7.2), facecolor="white", layout="constrained",
        sharex=True, sharey=True,
    )
    for ax, (scheme, (color, marker)) in zip(axes.flat, SCHEME_STYLES.items()):
        observed = [float(results[scheme, level, "optimized"]["SER"]) for level in levels]
        for field, (_, style) in THEORY_STYLES.items():
            ax.semilogy(levels, [theory[scheme, level][field] for level in levels],
                        color="#575e6c", linestyle=style, linewidth=1)
        ax.semilogy(levels, [value if value else math.nan for value in observed],
                    color=color, marker=marker, linewidth=1.5, markersize=4)
        zero_levels = [level for level, rate in zip(levels, observed) if rate == 0]
        # Marker position is in axes coordinates vertically, so it encodes no probability.
        ax.plot(zero_levels, [0.035] * len(zero_levels), marker="x", linestyle="none",
                color=color, transform=ax.get_xaxis_transform(), markersize=5)
        ax.set_title(scheme)
        ax.grid(axis="y", which="major", alpha=0.3)
    handles = [Line2D([], [], color="#202635", label="Observed SER")]
    handles += [
        Line2D([], [], color="#575e6c", linestyle=style, label=label)
        for label, style in THEORY_STYLES.values()
    ]
    handles.append(Line2D([], [], color="#202635", marker="x", linestyle="none",
                          label="Zero observed errors (axis marker)"))
    fig.suptitle("32-QAM SER · Simulation and theoretical reference")
    for ax in axes[-1]:
        ax.set_xlabel("Eb/N0 (dB)")
    fig.supylabel("SER (probability)")
    fig.legend(handles=handles, loc="outside lower center", ncols=2, fontsize=8)
    save_figure(fig, directory / "ser_theory_comparison")



def parse_levels(text: str) -> list[int]:
    try:
        values = [int(level) for level in text.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected comma-separated integer Eb/N0 levels") from error
    if values != sorted(set(values)) or not all(0 <= level <= 20 for level in values):
        raise argparse.ArgumentTypeError("Eb/N0 levels must be distinct and increasing in 0–20")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--builtin-qam32", type=Path, help="Export a built-in validation fixture")
    source.add_argument("--constellations", type=Path, help="Team constellations.csv")
    parser.add_argument("--simulator", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--theoretical-ser", type=Path, help="Overlay A's theoretical SER")
    parser.add_argument("--receipt", action="store_true", help="Write hashes for a full team run")
    parser.add_argument("--levels", type=parse_levels, default=list(range(21)))
    parser.add_argument("--max-symbols", type=int, default=2_000_000)
    parser.add_argument("--target-errors", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    if not 1 <= args.max_symbols <= (2**31 - 1) // BITS:
        parser.error("max-symbols must be positive and keep the bit count within 32-bit int")
    if not 1 <= args.target_errors < 2**31 or not 0 <= args.seed <= 2**32 - 21:
        parser.error("target-errors or seed out of range")
    if not args.simulator.is_file():
        parser.error("Build the C++ simulator and pass its executable with --simulator")

    if args.receipt and (not args.constellations or args.levels != list(range(21))):
        parser.error("A receipt requires the complete 0–20 dB grid and a team coordinate CSV")

    root = args.output_root
    metrics_dir = root / "results/metrics"
    figures_dir = root / "results/figures"
    mapped = root / "data/mapped_constellations.csv"
    mapping_metrics = metrics_dir / "mapping_metrics.csv"
    result_path = metrics_dir / "simulation_results.csv"
    optimizer = Path(__file__).with_name("mapping_optimizer.py")
    fixture = root / "data/builtin_constellations.csv"
    try:
        if args.builtin_qam32:
            constellations = read_builtin(args.builtin_qam32)
            fixture_rows = []
            for scheme, points in constellations.items():
                validate(scheme, points)
                fixture_rows.extend(
                    (scheme, p.point_id, p.i_raw, p.q_raw, p.i_norm, p.q_norm)
                    for p in points
                )
            write_csv(fixture, POINT_FIELDS, fixture_rows)
        input_csv = args.constellations or fixture
        if input_csv.resolve() in {path.resolve() for path in (mapped, mapping_metrics, result_path)}:
            raise ValueError("Constellation input must be distinct from generated CSV outputs")
        theory = read_theory(args.theoretical_ser, args.levels) if args.theoretical_ser else None
        input_hash = hashlib.sha256(input_csv.read_bytes()).hexdigest() if args.receipt else None
        subprocess.run(
            [sys.executable, str(optimizer), "--constellations", str(input_csv),
             "--mapped-output", str(mapped), "--metrics-output", str(mapping_metrics),
             "--seed", str(args.seed)],
            check=True,
        )
        subprocess.run(
            [str(args.simulator.resolve()), "--mapped-csv", str(mapped), str(result_path),
             ",".join(map(str, args.levels)), str(args.max_symbols), str(args.target_errors),
             str(args.seed)],
            check=True,
        )
        results = read_results(result_path, args.levels, args.max_symbols, args.target_errors, args.seed)
        plot_results(results, args.levels, figures_dir, builtin=args.builtin_qam32 is not None)
        if theory:
            plot_theory(results, theory, args.levels, figures_dir)
        if args.receipt:
            if hashlib.sha256(input_csv.read_bytes()).hexdigest() != input_hash:
                raise ValueError("Source constellation CSV changed during the run")
            receipt = {"data/constellations.csv": input_hash}
            for artifact in (mapped, mapping_metrics, result_path):
                receipt[artifact.relative_to(root).as_posix()] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (metrics_dir / "optimized_run_receipt.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n",
            )
            report_targets(results, args.levels)
        print(f"Validated {len(results)} rows and {len(results) // 2} paired SER comparisons.")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Simulation pipeline failed: {error}\n")


if __name__ == "__main__":
    main()
