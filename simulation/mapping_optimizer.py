"""Optimize the bit labels of 32-QAM constellations and report mapping metrics."""

import argparse
import ast
import csv
from dataclasses import dataclass
from itertools import combinations
import math
from pathlib import Path
import random
import re


SCHEMES = ("Rectangular", "Type1", "Type2", "Type3")
PARITY = {"Type1": (1, 1), "Type2": (0, 0), "Type3": (1, 0)}
POINT_FIELDS = ("scheme", "point_id", "I_raw", "Q_raw", "I_norm", "Q_norm")
METRIC_FIELDS = ("scheme", "mapping", "mean_neighbor_hamming", "gray_edge_ratio")
BITS = 5
SIZE = 1 << BITS
INITIAL = tuple(range(SIZE))
HAMMING = tuple(value.bit_count() for value in INITIAL)
DEFAULT_SEED = 20261128
RESTARTS = 24
STEPS = 12000


@dataclass(frozen=True)
class Point:
    point_id: int
    i_raw: int
    q_raw: int
    i_norm: str
    q_norm: str


def read_builtin(path: Path) -> dict[str, list[Point]]:
    """Read the original four C++ initializer blocks in declaration order."""
    source = re.sub(r"//[^\n]*|/\*.*?\*/", "", path.read_text(encoding="utf-8-sig"), flags=re.S)
    match = re.search(
        r"\bint\s+constellation\s*\[\s*NUM_CONSTELLATION\s*\]"
        r"\s*\[\s*32\s*\]\s*\[\s*2\s*\]\s*=\s*(\{[^;]*\});",
        source,
    )
    if not match:
        raise ValueError("Cannot locate the QAM32.cpp constellation initializer")
    arrays = ast.literal_eval(match[1].replace("{", "[").replace("}", "]"))
    if len(arrays) != len(SCHEMES):
        raise ValueError("Expected four C++ constellation blocks")

    constellations = {}
    for scheme, coordinates in zip(SCHEMES, arrays):
        if not isinstance(coordinates, list) or len(coordinates) != SIZE or any(
            not isinstance(pair, list) or len(pair) != 2
            or any(type(axis) is not int for axis in pair)
            for pair in coordinates
        ):
            raise ValueError(f"{scheme}: expected 32 integer coordinate pairs")
        scale = math.sqrt(sum(i * i + q * q for i, q in coordinates) / SIZE)
        if scale == 0:
            raise ValueError(f"{scheme}: zero average energy")
        constellations[scheme] = [
            Point(point_id, i, q, repr(i / scale), repr(q / scale))
            for point_id, (i, q) in enumerate(coordinates)
        ]
    return constellations


def read_csv(path: Path) -> dict[str, list[Point]]:
    """Read A's coordinates while retaining the original normalized decimal strings."""
    constellations = {scheme: [] for scheme in SCHEMES}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.reader(stream)
        if tuple(next(rows, ())) != POINT_FIELDS:
            raise ValueError("Incorrect constellation CSV header")
        for line, row in enumerate(rows, 2):
            if len(row) != len(POINT_FIELDS) or row[0] not in constellations:
                raise ValueError(f"Invalid constellation row {line}")
            scheme, point_id, i, q, i_norm, q_norm = row
            constellations[scheme].append(Point(int(point_id), int(i), int(q), i_norm, q_norm))
    for points in constellations.values():
        points.sort(key=lambda point: point.point_id)
    return constellations


def validate(scheme: str, points: list[Point]) -> None:
    if tuple(point.point_id for point in points) != INITIAL:
        raise ValueError(f"{scheme}: expected each point_id 0–31 exactly once")
    raw = {(p.i_raw, p.q_raw) for p in points}
    if len(raw) != SIZE or any(abs(axis) > 7 for pair in raw for axis in pair):
        raise ValueError(f"{scheme}: raw coordinates must be unique and in [-7, 7]")
    if scheme in PARITY and any((i % 2, q % 2) != PARITY[scheme] for i, q in raw):
        raise ValueError(f"{scheme}: raw coordinates do not meet the parity constraint")

    scale = math.sqrt(sum(i * i + q * q for i, q in raw) / SIZE)
    energy = 0.0
    for p in points:
        i_norm, q_norm = float(p.i_norm), float(p.q_norm)
        if not (
            math.isclose(i_norm, p.i_raw / scale, rel_tol=1e-9, abs_tol=1e-12)
            and math.isclose(q_norm, p.q_raw / scale, rel_tol=1e-9, abs_tol=1e-12)
        ):
            raise ValueError(f"{scheme}: incorrect normalized coordinates for point {p.point_id}")
        energy += i_norm * i_norm + q_norm * q_norm
    if not math.isclose(energy / SIZE, 1.0, rel_tol=1e-9):
        raise ValueError(f"{scheme}: normalized mean energy must equal 1")


def minimum_distance_edges(points: list[Point]) -> list[tuple[int, int]]:
    # Normalization multiplies all distances in a scheme by the same factor.
    # Compare squared distances on the integer lattice so ties are exact.
    distances = [
        ((p.i_raw - q.i_raw)**2 + (p.q_raw - q.q_raw)**2, p.point_id, q.point_id)
        for p, q in combinations(points, 2)
    ]
    minimum = min(distance for distance, _, _ in distances)
    return [(a, b) for distance, a, b in distances if distance == minimum]


def measure(labels: tuple[int, ...], edges: list[tuple[int, int]]) -> tuple[int, int]:
    distances = [HAMMING[labels[a] ^ labels[b]] for a, b in edges]
    return sum(distances), distances.count(1)


def optimize(edges: list[tuple[int, int]], seed: int) -> tuple[int, ...]:
    """Minimize the sum of Hamming distances over unordered minimum-distance pairs."""
    neighbors = [[] for _ in INITIAL]
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)

    lower_bound = len(edges)
    best = INITIAL
    best_cost, _ = measure(best, edges)
    if best_cost == lower_bound:
        return best

    rng = random.Random(seed)
    for restart in range(RESTARTS):
        labels = list(INITIAL)
        if restart:
            rng.shuffle(labels)
        cost, _ = measure(tuple(labels), edges)
        if cost < best_cost:
            best, best_cost = tuple(labels), cost
            if best_cost == lower_bound:
                return best
        for step in range(STEPS):
            a = rng.randrange(SIZE)
            b = rng.randrange(SIZE - 1)
            if b >= a:
                b += 1
            la, lb = labels[a], labels[b]
            # The edge between the swapped labels keeps its Hamming distance.
            delta = sum(
                HAMMING[lb ^ labels[n]] - HAMMING[la ^ labels[n]]
                for n in neighbors[a] if n != b
            ) + sum(
                HAMMING[la ^ labels[n]] - HAMMING[lb ^ labels[n]]
                for n in neighbors[b] if n != a
            )
            temperature = 2.0 * (0.08 / 2.0)**(step / (STEPS - 1))
            if delta <= 0 or rng.random() < math.exp(-delta / temperature):
                labels[a], labels[b] = lb, la
                cost += delta
                if cost < best_cost:
                    best, best_cost = tuple(labels), cost
                    if best_cost == lower_bound:
                        return best
    return best


def smoke_test(points: list[Point], optimized: tuple[int, ...], seed: int) -> None:
    """Use one AWGN channel realization and score its decisions with both maps."""
    ebn0_db = 10
    num_symbols = 50_000
    sigma = math.sqrt(1 / (2 * BITS * 10**(ebn0_db / 10)))
    rng = random.Random(seed)
    coordinates = [(float(p.i_norm), float(p.q_norm)) for p in points]
    symbol_errors = initial_errors = optimized_errors = 0
    for _ in range(num_symbols):
        source = rng.randrange(SIZE)
        i, q = coordinates[source]
        i_rx = i + rng.gauss(0.0, sigma)
        q_rx = q + rng.gauss(0.0, sigma)
        decision = min(
            INITIAL,
            key=lambda p: (i_rx - coordinates[p][0])**2 + (q_rx - coordinates[p][1])**2,
        )
        symbol_errors += source != decision
        initial_errors += HAMMING[source ^ decision]
        optimized_errors += HAMMING[optimized[source] ^ optimized[decision]]
    for mapping, errors in (("initial", initial_errors), ("optimized", optimized_errors)):
        print(
            f"AWGN {mapping}: Eb/N0={ebn0_db} dB, seed={seed}, symbols={num_symbols}, "
            f"symbol_errors={symbol_errors}, bit_errors={errors}, "
            f"SER={symbol_errors / num_symbols:.9g}, BER={errors / (BITS * num_symbols):.9g}"
        )


def write_csv(path: Path, fields: tuple[str, ...], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--qam32-source", type=Path, help="Professor's QAM32.cpp")
    source.add_argument("--constellations", type=Path, help="A's 128-row constellation CSV")
    parser.add_argument("--mapped-output", required=True, type=Path)
    parser.add_argument("--metrics-output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--smoke-type", choices=list(PARITY), help="Run a paired 10 dB AWGN check")
    args = parser.parse_args()

    input_path = args.qam32_source or args.constellations
    if len({path.resolve() for path in (input_path, args.mapped_output, args.metrics_output)}) != 3:
        parser.error("Input and output paths must be distinct")

    try:
        constellations = read_builtin(input_path) if args.qam32_source else read_csv(input_path)
        mapped_rows, metric_rows = [], []
        optimized_by_scheme = {}
        for index, (scheme, points) in enumerate(constellations.items()):
            validate(scheme, points)
            edges = minimum_distance_edges(points)
            initial_cost, initial_gray = measure(INITIAL, edges)
            if args.qam32_source and scheme == "Rectangular" and (len(edges), initial_gray) != (52, 52):
                raise ValueError("Built-in Rectangular must have 52 initial Gray edges")

            seed = args.seed + index
            optimized = optimize(edges, seed)
            optimized_cost, _ = measure(optimized, edges)
            if tuple(sorted(optimized)) != INITIAL or optimized_cost > initial_cost:
                raise RuntimeError(f"{scheme}: optimizer returned an invalid mapping")

            print(f"{scheme}: minimum-distance pairs={len(edges)}, search_seed={seed}")
            for mapping, labels in (("initial", INITIAL), ("optimized", optimized)):
                cost, gray = measure(labels, edges)
                mean = cost / len(edges)
                ratio = gray / len(edges)
                metric_rows.append((scheme, mapping, mean, ratio))
                print(f"  {mapping}: cost={cost}, mean_hamming={mean:.9g}, gray_edges={gray}/{len(edges)}")
            if optimized_cost > len(edges):
                print("  Complete Gray mapping was not found in this search.")
            optimized_by_scheme[scheme] = optimized
            mapped_rows.extend(
                (scheme, p.point_id, p.i_raw, p.q_raw, p.i_norm, p.q_norm, format(label, "05b"))
                for p, label in zip(points, optimized)
            )
        write_csv(args.mapped_output, (*POINT_FIELDS, "bit_label"), mapped_rows)
        write_csv(args.metrics_output, METRIC_FIELDS, metric_rows)
        if args.smoke_type:
            smoke_test(constellations[args.smoke_type], optimized_by_scheme[args.smoke_type], args.seed)
    except (OSError, SyntaxError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Mapping optimization failed: {error}\n")


if __name__ == "__main__":
    main()
