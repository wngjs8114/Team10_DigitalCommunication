"""Validate A's SER reference and estimate Eb/N0 at bracketed error rates."""

import csv
import math
from pathlib import Path

from mapping_optimizer import SCHEMES


THEORY_STYLES = {
    "nearest_approx": ("Nearest-neighbor approximation", "--"),
    "pairwise_lower_bound": ("Pairwise lower bound", "-."),
    "union_upper_bound": ("Union upper bound", ":"),
}
TARGETS = (1e-2, 1e-3, 1e-6)


def read_theory(path: Path, levels: list[int]) -> dict[tuple[str, int], dict[str, float]]:
    """Read A's probabilities, preserving the distinction between bounds and approximation."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("scheme", "ebn0_db", *THEORY_STYLES)
        if tuple(reader.fieldnames or ()) != expected:
            raise ValueError("Unexpected theoretical SER header")
        theory = {}
        for line, row in enumerate(reader, 2):
            key = row["scheme"], int(row["ebn0_db"])
            values = {name: float(row[name]) for name in THEORY_STYLES}
            if (
                key in theory or key[0] not in SCHEMES or not 0 <= key[1] <= 20
                or any(not 0 < value <= 1 for value in values.values())
                or values["pairwise_lower_bound"] > values["union_upper_bound"]
            ):
                raise ValueError(f"Invalid theoretical SER row {line}")
            theory[key] = values
    if any((scheme, level) not in theory for scheme in SCHEMES for level in levels):
        raise ValueError("Theoretical SER must cover all simulated scheme and Eb/N0 pairs")
    return theory


def estimate_ebn0(levels: list[int], rates: list[float], goal: float) -> float | None:
    """Interpolate a unique positive-rate bracket linearly in log10(rate)."""
    crossings = [float(level) for level, rate in zip(levels, rates) if rate == goal]
    for x0, x1, y0, y1 in zip(levels, levels[1:], rates, rates[1:]):
        if 0 < min(y0, y1) < goal < max(y0, y1):
            t = (math.log10(goal) - math.log10(y0)) / (math.log10(y1) - math.log10(y0))
            crossings.append(x0 + t * (x1 - x0))
    return crossings[0] if len(crossings) == 1 else None


def report_targets(
    results: dict[tuple[str, int, str], dict[str, str]], levels: list[int],
) -> None:
    comparisons = [
        (metric, ("Rectangular", "optimized"), (scheme, "optimized"))
        for metric in ("SER", "BER") for scheme in SCHEMES[1:]
    ] + [("BER", (scheme, "initial"), (scheme, "optimized")) for scheme in SCHEMES]
    for metric, reference, alternative in comparisons:
        reference_rates = [
            float(results[reference[0], level, reference[1]][metric]) for level in levels
        ]
        alternative_rates = [
            float(results[alternative[0], level, alternative[1]][metric]) for level in levels
        ]
        differences = []
        for goal in TARGETS:
            first = estimate_ebn0(levels, reference_rates, goal)
            second = estimate_ebn0(levels, alternative_rates, goal)
            value = "unavailable" if first is None or second is None else f"{first - second:+.3f} dB"
            differences.append(f"{goal:g}: {value}")
        print(f"{metric} {'/'.join(reference)} minus {'/'.join(alternative)}: {', '.join(differences)}")
