"""Search integer 32-QAM layouts and analyze their AWGN symbol errors."""

import argparse
from collections import Counter
import csv
from itertools import product
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import ndtr

SIZE = 32
ROOT = Path(__file__).resolve().parents[1]
PARITY = {"Type1": (1, 1), "Type2": (0, 0), "Type3": (1, 0)}
STYLE = {
    "Rectangular": ("#64748B", "o"),
    "Type1": ("#2563EB", "s"),
    "Type2": ("#0D9488", "^"),
    "Type3": ("#9333EA", "D"),
}


def squared_distances(points: np.ndarray) -> np.ndarray:
    return np.sum((points[:, None] - points[None, :]) ** 2, axis=2)


def search(parity: tuple[int, int], rng: np.random.Generator, restarts: int) -> np.ndarray:
    """Use best-improving single swaps from low-energy and random starts."""
    grid = np.array([
        (i, q) for i, q in product(range(-7, 8), repeat=2)
        if (i % 2, q % 2) == parity
    ])
    energy = np.sum(grid ** 2, axis=1)
    distances = squared_distances(grid)
    first, second = np.triu_indices(SIZE, 1)
    removal_masks = [(first != k) & (second != k) for k in range(SIZE)]

    def score(minimum, total_energy, neighbors):
        # Multiply by SIZE to compare d_min squared after normalization.
        return minimum * SIZE / total_energy, -neighbors

    best_score = (-1.0, 0)
    for restart in range(restarts):
        if restart == 0:
            selected = np.argsort(energy, kind="stable")[:SIZE]
        else:
            selected = rng.choice(len(grid), SIZE, replace=False)
        while True:
            pairs = distances[selected[first], selected[second]]
            minimum = pairs.min()
            total = energy[selected].sum()
            current = score(minimum, total, np.count_nonzero(pairs == minimum))
            swap_score = current
            swap = None
            outside = np.setdiff1d(np.arange(len(grid)), selected)
            for k, keep_pairs in enumerate(removal_masks):
                kept = pairs[keep_pairs]
                incoming = distances[np.ix_(outside, np.delete(selected, k))]
                minimum = np.minimum(kept.min(), incoming.min(axis=1))
                neighbors = (kept[None, :] == minimum[:, None]).sum(axis=1)
                neighbors += (incoming == minimum[:, None]).sum(axis=1)
                totals = total - energy[selected[k]] + energy[outside]
                j = np.lexsort((neighbors, -minimum / totals))[0]
                candidate = score(minimum[j], totals[j], neighbors[j])
                if candidate > swap_score:
                    swap_score, swap = candidate, (k, outside[j])
            if swap is None:
                break
            selected[swap[0]] = swap[1]
        if current > best_score:
            best_score = current
            best_points = grid[np.sort(selected)]
    return best_points


def load_rectangular(path: Path) -> np.ndarray:
    """Read professor coordinates in their supplied row order."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["I_raw", "Q_raw"]:
            raise ValueError("Rectangular CSV must have the header I_raw,Q_raw")
        points = [(int(row["I_raw"]), int(row["Q_raw"])) for row in rows]
    if len(points) != SIZE or len(set(points)) != SIZE:
        raise ValueError("Rectangular CSV must contain exactly 32 distinct points")
    if any(abs(value) > 7 for point in points for value in point):
        raise ValueError("Rectangular coordinates must be in [-7, 7]")
    return np.asarray(points)


def write_csv(path: Path, header: str, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header.split(","))
        writer.writerows(rows)


def save_figure(fig, directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / f"{name}.png", dpi=300)
    fig.savefig(directory / f"{name}.pdf")
    plt.close(fig)


def analyze(layouts: dict[str, np.ndarray], output: Path, candidates_only: bool) -> None:
    coordinates, geometry, distribution, ser = [], [], [], []
    figures = output / "results/figures/constellations"
    fig_ser, ax_ser = plt.subplots(layout="constrained")
    ebn0_db = np.arange(21)
    sigma_squared = 1 / (10 * 10 ** (ebn0_db / 10))
    normalized_limit = max(
        np.abs(points).max() / np.sqrt(np.square(points).sum() / SIZE)
        for points in layouts.values()
    ) * 1.15
    for scheme, points in layouts.items():
        raw_energy = np.square(points).sum() / SIZE
        factor = 1 / np.sqrt(raw_energy)
        normalized = points * factor
        coordinates.extend(
            (scheme, point_id, *raw, *norm)
            for point_id, (raw, norm) in enumerate(zip(points, normalized))
        )
        first, second = np.triu_indices(SIZE, 1)
        counts = sorted(Counter(squared_distances(points)[first, second]).items())
        raw_d2, pair_count = counts[0]
        geometry.append((scheme, raw_energy, factor, np.sqrt(raw_d2) * factor,
                         2 * pair_count / SIZE))
        union_bound = np.zeros(len(ebn0_db))
        for distance_squared, count in counts:
            distance = np.sqrt(distance_squared) * factor
            distribution.append((scheme, distance_squared, distance, count))
            contribution = 2 * count / SIZE * ndtr(-distance / (2 * np.sqrt(sigma_squared)))
            if distance_squared == raw_d2:
                nearest = contribution
            union_bound += contribution
        # Average the strongest pairwise event for each transmitted symbol.
        all_distances = squared_distances(points)
        np.fill_diagonal(all_distances, np.iinfo(all_distances.dtype).max)
        distances_to_nearest = np.sqrt(all_distances.min(axis=1)) * factor
        lower_bound = ndtr(-distances_to_nearest[:, None] / (2 * np.sqrt(sigma_squared))).mean(axis=0)
        upper_bound = np.minimum(union_bound, 1)
        ser.extend(zip([scheme] * len(ebn0_db), ebn0_db, nearest, lower_bound, upper_bound))

        color, marker = STYLE[scheme]
        fig, ax = plt.subplots(layout="constrained")
        ax.scatter(*normalized.T, color=color, marker=marker)
        ax.set(title=f"{scheme} constellation", xlabel="In-phase (normalized)",
               ylabel="Quadrature (normalized)", xlim=(-normalized_limit, normalized_limit),
               ylim=(-normalized_limit, normalized_limit), aspect="equal")
        ax.grid(alpha=0.25)
        save_figure(fig, figures, f"constellation_{scheme.lower()}")
        ax_ser.semilogy(ebn0_db, nearest, color=color, marker=marker,
                        markevery=4, label=scheme)

    ax_ser.set(title="Nearest-distance SER approximation",
               xlabel="Eb/N0 (dB)", ylabel="Symbol error probability")
    ax_ser.grid(alpha=0.25)
    ax_ser.legend()
    save_figure(fig_ser, figures, "theoretical_ser")
    suffix = "_candidates" if candidates_only else ""
    write_csv(output / f"data/constellations{suffix}.csv",
              "scheme,point_id,I_raw,Q_raw,I_norm,Q_norm", coordinates)
    metrics = output / "results/metrics"
    write_csv(metrics / f"geometry_metrics{suffix}.csv",
              "scheme,Es_raw,normalization_factor,d_min,mean_nearest_neighbors", geometry)
    write_csv(metrics / f"distance_distribution{suffix}.csv",
              "scheme,distance_squared_raw,distance_norm,unordered_pairs", distribution)
    write_csv(metrics / f"theoretical_ser{suffix}.csv",
              "scheme,ebn0_db,nearest_approx,pairwise_lower_bound,union_upper_bound", ser)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rectangular", type=Path, help="Professor CSV with I_raw,Q_raw")
    mode.add_argument("--candidates-only", action="store_true")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--seed", type=int, default=10)
    parser.add_argument("--restarts", type=int, default=32)
    args = parser.parse_args()
    if args.restarts < 1 or args.seed < 0:
        parser.error("restarts must be positive and seed must be nonnegative")
    layouts = {}
    if args.rectangular:
        try:
            layouts["Rectangular"] = load_rectangular(args.rectangular)
        except (ValueError, OSError, TypeError) as exc:
            parser.error(str(exc))
    for scheme, parity in PARITY.items():
        layouts[scheme] = search(parity, np.random.default_rng(args.seed), args.restarts)
    output = args.output_root or (ROOT / "design/candidates" if args.candidates_only else ROOT)
    analyze(layouts, output, args.candidates_only)


if __name__ == "__main__":
    main()
