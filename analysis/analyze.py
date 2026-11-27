import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
SCHEMES = ["Rectangular", "Type1", "Type2", "Type3"]
COLORS = ["#64748B", "#2563EB", "#0D9488", "#9333EA"]
MARKERS = ["o", "s", "^", "D"]
COLUMNS = ["scheme", "point_id", "I_raw", "Q_raw", "I_norm", "Q_norm"]
PARITIES = {"Type1": [1, 1], "Type2": [0, 0], "Type3": [1, 0]}
RECTANGULAR = {(i, q) for i in range(-3, 4, 2) for q in range(-7, 8, 2)}
SEED = 2026
TEST_SAMPLES = 10_000
PLOT_LIMIT = 2
BETA = 0.35
SPS = 8
SPAN = 10
FRAMES = 2000
FRAME_SYMBOLS = 512
GUARD = 8
ROLL_OFFS = (0.15, BETA, 0.60)
SAMPLE_RATES = (4, SPS, 16, 32)


def load(path: Path) -> pd.DataFrame:
    """Read and validate either shared constellation CSV schema."""
    # Python float preserves the nearest binary64 value of each decimal token.
    df = pd.read_csv(
        path, dtype={"bit_label": "string"}, converters={"I_norm": float, "Q_norm": float},
    )
    if not isinstance(df.index, pd.RangeIndex):
        raise ValueError("Unexpected extra fields in CSV rows.")
    if df.columns.tolist() not in (COLUMNS, COLUMNS + ["bit_label"]):
        raise ValueError("Unexpected columns. See docs/DATA_FORMAT.md.")
    if len(df) != 128 or set(df.scheme) != set(SCHEMES):
        raise ValueError("Expected 128 rows across the four named schemes.")
    for name, group in df.groupby("scheme"):
        raw = group[["I_raw", "Q_raw"]].to_numpy(float)
        norm = group[["I_norm", "Q_norm"]].to_numpy(float)
        if len(group) != 32 or set(group.point_id) != set(range(32)):
            raise ValueError(f"{name}: expected one occurrence of each point_id 0–31.")
        if (not np.isfinite(raw).all() or not np.all(raw == np.round(raw))
                or np.max(np.abs(raw)) > 7):
            raise ValueError(f"{name}: raw coordinates must be integers in [-7, 7].")
        points = set(map(tuple, raw))
        if len(points) != 32:
            raise ValueError(f"{name}: duplicate raw coordinates.")
        if name == "Rectangular":
            if points != RECTANGULAR:
                raise ValueError(f"{name}: coordinates differ from the reference grid.")
        elif not np.all(raw % 2 == PARITIES[name]):
            raise ValueError(f"{name}: raw coordinate parity does not match the scheme.")
        scale = np.sqrt(np.mean(np.sum(raw**2, axis=1)))
        if not np.allclose(norm, raw / scale, rtol=0, atol=1e-7):
            raise ValueError(f"{name}: normalized coordinates differ from raw / sqrt(Es_raw).")
        if not np.isclose(np.mean(np.sum(norm**2, axis=1)), 1, rtol=0, atol=2e-7):
            raise ValueError(f"{name}: normalized average energy must be 1.")
        if "bit_label" in group and set(group.bit_label) != {f"{i:05b}" for i in range(32)}:
            raise ValueError(f"{name}: expected all 32 distinct five-bit labels.")
    return df


def validate_mapping(mapped: pd.DataFrame, reference: pd.DataFrame) -> None:
    """Check point IDs and coordinates against A's input, allowing row order to vary."""
    columns = ["I_raw", "Q_raw", "I_norm", "Q_norm"]
    keys = ["scheme", "point_id"]
    actual = mapped.set_index(keys).sort_index()[columns]
    expected = reference.set_index(keys).sort_index()[columns]
    if not np.array_equal(actual.to_numpy(), expected.to_numpy()):
        raise ValueError("Mapping changes coordinates or point IDs relative to A's CSV.")


def empirical_ccdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return unique thresholds and strict empirical exceedance probabilities."""
    thresholds, counts = np.unique(values, return_counts=True)
    return thresholds, (len(values) - counts.cumsum()) / len(values)


def save(fig,path):
    import matplotlib.pyplot as plt
    fig.savefig(path.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)

def rrc(beta,sps,span):
    half = span * sps // 2
    t = np.arange(-half, half + 1) / sps
    if beta == 0:
        h = np.sinc(t)
        return h / np.linalg.norm(h)
    h=np.empty_like(t); z=np.isclose(t,0); s=np.isclose(abs(t),1/(4*beta)); m=~(z|s)
    h[z]=1-beta+4*beta/np.pi
    h[s]=beta/np.sqrt(2)*((1+2/np.pi)*np.sin(np.pi/(4*beta))+(1-2/np.pi)*np.cos(np.pi/(4*beta)))
    h[m]=(np.sin(np.pi*t[m]*(1-beta))+4*beta*t[m]*np.cos(np.pi*t[m]*(1+beta)))/(np.pi*t[m]*(1-(4*beta*t[m])**2))
    return h/np.linalg.norm(h)

def constellation_metrics(name: str, raw: np.ndarray, points: np.ndarray) -> dict:
    """Calculate symbol power, geometry and population statistics."""
    energy = np.sum(points**2, axis=1)
    distances = np.linalg.norm(points[:, None] - points[None, :], axis=2)
    np.fill_diagonal(distances, np.inf)
    raw_set = set(map(tuple, raw))

    def symmetric(transformed: np.ndarray) -> int:
        return int(set(map(tuple, transformed)) == raw_set)

    papr = energy.max() / energy.mean()
    return dict(
        scheme=name, Es_norm=energy.mean(), d_min=distances.min(),
        papr_linear=papr, papr_db=10 * np.log10(papr),
        mean_I=points[:, 0].mean(), mean_Q=points[:, 1].mean(),
        energy_I=np.mean(points[:, 0]**2), energy_Q=np.mean(points[:, 1]**2),
        cov_IQ=np.cov(points.T, bias=True)[0, 1],
        sym_origin=symmetric(-raw), sym_I=symmetric(raw * [1, -1]),
        sym_Q=symmetric(raw * [-1, 1]), sym_rot90=symmetric(raw[:, ::-1] * [-1, 1]),
    )


def receiver_metrics(name: str, raw: np.ndarray, points: np.ndarray, test: np.ndarray) -> dict:
    """Compare direct ML to column-grouped ML, including distance ties."""
    columns = np.unique(points[:, 0])
    groups = [np.flatnonzero(points[:, 0] == column) for column in columns]
    full = len(raw) == len(columns) * len(np.unique(points[:, 1]))
    distances = np.sum((test[:, None] - points)**2, axis=2)
    brute = np.argmin(distances, axis=1)
    # Reuse each winning Q term when adding the one I term for its column.
    q_squared = (test[:, None, 1] - points[:, 1])**2
    samples = np.arange(len(test))
    winners = np.stack([idx[np.argmin(q_squared[:, idx], axis=1)] for idx in groups], axis=1)
    i_squared = (test[:, None, 0] - points[[idx[0] for idx in groups], 0])**2
    totals = i_squared + q_squared[samples[:, None], winners]
    pred = winners[samples, np.argmin(totals, axis=1)]
    minimum = distances[samples, brute]
    same_distance = np.isclose(distances[samples, pred], minimum, rtol=0, atol=1e-12)
    ties = np.count_nonzero(np.isclose(distances, minimum[:, None], rtol=0, atol=1e-12), axis=1) > 1
    if not same_distance.all() or np.any((pred != brute) & ~ties):
        raise RuntimeError(f"{name}: grouped ML disagrees with brute-force ML.")
    independent_mismatches = None
    if full:
        i_levels, i_first, i_index = np.unique(points[:, 0], return_index=True, return_inverse=True)
        q_levels, q_first, q_index = np.unique(points[:, 1], return_index=True, return_inverse=True)
        lookup = np.empty((len(i_levels), len(q_levels)), dtype=int)
        lookup[i_index, q_index] = np.arange(len(raw))
        nearest_i = np.argmin((test[:, None, 0] - points[i_first, 0])**2, axis=1)
        nearest_q = np.argmin((test[:, None, 1] - points[q_first, 1])**2, axis=1)
        independent = lookup[nearest_i, nearest_q]
        independent_mismatch = independent != brute
        if (not np.isclose(distances[samples, independent], minimum, rtol=0, atol=1e-12).all()
                or np.any(independent_mismatch & ~ties)):
            raise RuntimeError(f"{name}: independent I/Q ML disagrees with brute-force ML.")
        independent_mismatches = int(independent_mismatch.sum())

    return dict(
        scheme=name, brute_candidates=32, brute_comparisons=31, I_columns=len(columns),
        grouped_final_candidates=len(columns), cartesian_product=int(full),
        test_samples=len(test), distance_agreement=1, tie_samples=int(ties.sum()),
        index_mismatches=int(np.count_nonzero(pred != brute)),
        independent_index_mismatches=independent_mismatches,
    )


def receiver_operation_counts(points: np.ndarray, scheme: str) -> list[dict]:
    """Counts per received symbol for linear scans with precomputed group tables."""
    n = len(points)
    i_count, q_count = (len(np.unique(points[:, axis])) for axis in (0, 1))
    modes = [
        ("brute_force", 2 * n, n, 2 * n, n - 1),
        ("grouped", n + i_count, i_count, n + i_count, (n - i_count) + (i_count - 1)),
    ]
    if n == i_count * q_count:
        levels = i_count + q_count
        modes.append(("independent_iq", levels, 0, levels, levels - 2))
    return [
        dict(scheme=scheme, receiver=mode, case=case, subtractions=sub, additions=add,
             multiplications=mul, comparisons=cmp)
        for mode, sub, add, mul, cmp in modes
        for case in ("average", "worst")
    ]


def frame_waveform(symbols: np.ndarray, taps: np.ndarray, sps: int, guard: int) -> np.ndarray:
    """Sample complete symbol intervals after compensating the FIR group delay."""
    from scipy.signal import upfirdn

    delay = (len(taps) - 1) // 2
    if guard * sps < delay or symbols.shape[-1] <= 2 * guard:
        raise ValueError("Frame must contain enough guard and measurement symbols.")
    start = guard * sps + delay
    stop = start + (symbols.shape[-1] - 2 * guard) * sps
    return upfirdn(taps, symbols, up=sps, axis=-1)[..., start:stop]


def waveform_papr(symbols: np.ndarray, taps: np.ndarray, sps: int) -> np.ndarray:
    """Compute per-frame PAPR in dB using bounded batches."""
    frame_papr = []
    for start in range(0, len(symbols), 128):
        signal = frame_waveform(symbols[start:start + 128], taps, sps, GUARD)
        power = np.abs(signal)**2
        frame_papr.extend(10 * np.log10(power.max(axis=1) / power.mean(axis=1)))
    return np.asarray(frame_papr)


def ml_cells(points: np.ndarray, limit: float = PLOT_LIMIT) -> list[np.ndarray]:
    """Clip each ML cell to the plot box using pairwise bisector half-planes."""
    box = [np.array(xy, dtype=float) for xy in
           [(-limit, -limit), (limit, -limit), (limit, limit), (-limit, limit)]]
    cells = []
    for i, point in enumerate(points):
        polygon = box
        for j, rival in enumerate(points):
            if i == j or not polygon:
                continue
            normal = rival - point
            midpoint = (point + rival) / 2
            clipped = []
            for start, end in zip(polygon, polygon[1:] + polygon[:1]):
                a = np.dot(start - midpoint, normal)
                b = np.dot(end - midpoint, normal)
                if a <= 0:
                    clipped.append(start)
                if (a < 0 < b) or (b < 0 < a):
                    clipped.append(start + (end - start) * a / (a - b))
            polygon = clipped
        cells.append(np.asarray(polygon))
    return cells


def plot_boundaries(points, cells, labels, name, color, marker, figdir, baseline):
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Patch

    qualifier = " (baseline)" if baseline else ""

    def draw(ax, colors, edges):
        ax.add_collection(PolyCollection(cells, facecolors=colors, edgecolors=edges,
                                         linewidths=0.5, antialiased=False))
        ax.scatter(*points.T, c=color, marker=marker, s=26, edgecolors="white",
                   linewidths=0.6, zorder=3)
        ax.set(xlim=(-PLOT_LIMIT, PLOT_LIMIT), ylim=(-PLOT_LIMIT, PLOT_LIMIT),
               xlabel="In-phase (normalized)", ylabel="Quadrature (normalized)", aspect="equal")

    fig, ax = plt.subplots(figsize=(6, 6))
    draw(ax, "#f1f5f9", "#475569")
    ax.set_title(f"{name}: symbol ML regions{qualifier}")
    save(fig, figdir / f"ser_boundary_{name}")
    if labels is None:
        return

    bit_colors = ["#dbeafe", "#fecaca"]
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout="constrained")
    for j, ax in enumerate(axes.flat[:5]):
        draw(ax, [bit_colors[int(label[j])] for label in labels], "none")
        ax.set_title(f"Bit {j + 1} (MSB first)")
    axes.flat[5].axis("off")
    axes.flat[5].legend(handles=[Patch(color=c, label=f"Bit {i}") for i, c in enumerate(bit_colors)],
                        loc="center", frameon=False)
    fig.suptitle(f"{name}: symbol ML bit decisions{qualifier}")
    save(fig, figdir / f"ber_boundary_{name}")


def main():
    parser = argparse.ArgumentParser(description="Analyze validated 32-QAM constellations.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference", type=Path, help="A's CSV for checking B's mapping")
    parser.add_argument("--out", type=Path, required=True, help="A new output directory")
    parser.add_argument("--baseline", action="store_true", help="Label outputs as baseline")
    parser.add_argument("--waveform", action="store_true")
    parser.add_argument("--waveform-sweep", action="store_true", help="Run RRC roll-off and SPS sweep")
    parser.add_argument("--metrics-only", action="store_true", help="Skip figures and waveform")
    args = parser.parse_args()
    args.waveform = args.waveform or args.waveform_sweep
    if args.metrics_only and args.waveform:
        parser.error("--metrics-only cannot be combined with --waveform.")
    try:
        df = load(args.input)
        mapped = "bit_label" in df
        if args.input.resolve() == Path(__file__).with_name("baseline").joinpath(
            "baseline_mapped_constellations.csv"
        ).resolve() and not args.baseline:
            raise ValueError("Use --baseline with the bundled reference CSV.")
        if args.reference:
            if not mapped:
                raise ValueError("--reference is for mapped input.")
            validate_mapping(df, load(args.reference))
        elif mapped and not args.baseline:
            raise ValueError("Mapped input requires --reference with A's constellation CSV.")
        if not args.metrics_only:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        if args.waveform:
            import scipy.signal
        out = args.out
        out.mkdir(parents=True, exist_ok=False)
    except (ImportError, OSError, ValueError) as error:
        parser.error(str(error))

    figdir = out / "figures"
    if not args.metrics_only:
        figdir.mkdir()
    rows, complexity, operations, wave, summaries = [], [], [], [], []
    test = np.random.default_rng(SEED).uniform(-3, 3, (TEST_SAMPLES, 2))
    if args.waveform:
        rng = np.random.default_rng(SEED)
        indices = rng.integers(0, 32, (FRAMES, FRAME_SYMBOLS + 2 * GUARD))
        conditions = ([(beta, sps) for beta in ROLL_OFFS for sps in SAMPLE_RATES]
                      if args.waveform_sweep else [(BETA, SPS)])
        taps_by_condition = {(beta, sps): rrc(beta, sps, SPAN) for beta, sps in conditions}

    for name, color, marker in zip(SCHEMES, COLORS, MARKERS):
        g = df[df.scheme == name].sort_values("point_id")
        p = g[["I_raw", "Q_raw"]].to_numpy(int)
        q = g[["I_norm", "Q_norm"]].to_numpy(float)
        rows.append(constellation_metrics(name, p, q))
        complexity.append(receiver_metrics(name, p, q, test))
        operations.extend(receiver_operation_counts(q, name))
        if args.metrics_only:
            continue
        labels = g.bit_label.to_numpy() if "bit_label" in g else None
        plot_boundaries(q, ml_cells(q), labels, name, color, marker, figdir, args.baseline)
        if args.waveform:
            symbols = (q[:, 0] + 1j * q[:, 1])[indices]
            for (beta, sps), taps in taps_by_condition.items():
                papr = waveform_papr(symbols, taps, sps)
                p95, p99 = np.quantile(papr, [0.95, 0.99], method="linear")
                summaries.append(dict(
                    scheme=name, roll_off=beta, samples_per_symbol=sps, frames=len(papr),
                    mean_papr_db=papr.mean(), p95_papr_db=p95, p99_papr_db=p99,
                ))
                if (beta, sps) == (BETA, SPS):
                    wave.extend(dict(scheme=name, frame=i, papr_db=value)
                                for i, value in enumerate(papr))
    metrics = pd.DataFrame(rows)
    metrics.to_csv(out / "constellation_metrics.csv", index=False)
    pd.DataFrame(complexity).astype({"independent_index_mismatches": "Int64"}).to_csv(
        out / "receiver_complexity.csv", index=False,
    )
    pd.DataFrame(operations).to_csv(out / "receiver_operation_counts.csv", index=False)
    qualifier = " (baseline)" if args.baseline else ""
    if not args.metrics_only:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(SCHEMES, metrics.papr_db, color=COLORS)
        ax.set(ylabel="Symbol PAPR (dB)", title=f"Constellation PAPR{qualifier}")
        ax.bar_label(ax.containers[0], fmt="%.3f", padding=3)
        ax.margins(y=0.15)
        save(fig, figdir / "papr_comparison")
    if wave:
        w = pd.DataFrame(wave)
        w.to_csv(out / "waveform_papr.csv", index=False)
        fig, ax = plt.subplots(figsize=(7, 5));
        pd.DataFrame(summaries).to_csv(out / "waveform_papr_summary.csv", index=False)
        for name, color, marker in zip(SCHEMES, COLORS, MARKERS):
            thresholds, probability = empirical_ccdf(w.loc[w.scheme == name, "papr_db"].to_numpy())
            positive = probability > 0
            ax.step(thresholds[positive], probability[positive], where="post", label=name, color=color, marker=marker, markevery=250, markersize=3)
        ax.set_yscale("log")
        ax.set(xlabel="Frame PAPR (dB)", ylabel="Empirical Pr(PAPR > x)",
               title=f"RRC waveform PAPR{qualifier}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        save(fig, figdir / "papr_ccdf")
    metadata = {
        "baseline": args.baseline,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "seed": SEED,
        "receiver_test_samples": TEST_SAMPLES,
        "decision_geometry": "clipped ML half-planes",
        "decision_axis_limit": PLOT_LIMIT,
    }
    if args.reference:
        metadata["reference_sha256"] = hashlib.sha256(args.reference.read_bytes()).hexdigest()
    if args.waveform:
        metadata["waveform"] = {
            "roll_off": BETA, "samples_per_symbol": SPS, "span_symbols": SPAN,
            "frames": FRAMES, "frame_symbols": FRAME_SYMBOLS, "guard_symbols": GUARD,
            "conditions": [{"roll_off": beta, "samples_per_symbol": sps} for beta, sps in conditions],
        }
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(metrics.to_string(index=False))
    print("Saved:", out)
if __name__=='__main__': main()
