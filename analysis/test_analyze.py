import csv
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.analyze import (
    constellation_metrics,
    empirical_ccdf,
    frame_waveform,
    load,
    ml_cells,
    receiver_metrics,
    receiver_operation_counts,
    rrc,
    validate_mapping,
)

BASELINE = Path(__file__).with_name("baseline") / "baseline_mapped_constellations.csv"


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load(BASELINE)
        rectangular = cls.data.loc[cls.data.scheme == "Rectangular"].sort_values("point_id")
        cls.raw = rectangular[["I_raw", "Q_raw"]].to_numpy(int)
        cls.points = rectangular[["I_norm", "Q_norm"]].to_numpy(float)

    def test_rectangular_papr_and_symmetry(self):
        energy = np.sum(self.raw**2, axis=1)
        self.assertEqual(energy.mean(), 26)
        self.assertEqual(energy.max(), 58)
        metrics = constellation_metrics("Rectangular", self.raw, self.points)
        self.assertAlmostEqual(metrics["Es_norm"], 1)
        self.assertAlmostEqual(metrics["papr_linear"], 58 / 26)
        self.assertAlmostEqual(metrics["papr_db"], 10 * math.log10(58 / 26))
        self.assertAlmostEqual(metrics["d_min"], 2 / math.sqrt(26))
        self.assertEqual([metrics[key] for key in ("sym_origin", "sym_I", "sym_Q", "sym_rot90")],
                         [1, 1, 1, 0])

    def test_receiver_boundary_tie(self):
        metrics = receiver_metrics("Rectangular", self.raw, self.points, np.array([[0., 0.]]))
        self.assertEqual(metrics["tie_samples"], 1)
        self.assertEqual(metrics["distance_agreement"], 1)

    def test_mapping_association_and_leading_zero(self):
        self.assertEqual(self.data.iloc[0].bit_label, "00000")
        reference = self.data.drop(columns="bit_label")
        validate_mapping(self.data.iloc[::-1], reference)
        changed = reference.copy()
        changed.loc[[0, 1], "point_id"] = [1, 0]
        with self.assertRaisesRegex(ValueError, "point IDs"):
            validate_mapping(self.data, changed)

    def test_invalid_inputs(self):
        cases = [
            ("point_id", 1, "point_id"),
            ("I_norm", 0, "normalized coordinates"),
            ("bit_label", "00001", "five-bit labels"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.csv"
            for column, value, message in cases:
                with self.subTest(column=column):
                    rows = self.data.copy()
                    rows.loc[0, column] = value
                    rows.to_csv(path, index=False)
                    with self.assertRaisesRegex(ValueError, message):
                        load(path)

    def test_csv_binary64_precision(self):
        with BASELINE.open(encoding="utf-8", newline="") as source:
            expected = [(float(row["I_norm"]), float(row["Q_norm"]))
                        for row in csv.DictReader(source)]
        actual = self.data[["I_norm", "Q_norm"]].to_numpy()
        np.testing.assert_array_equal(actual.view(np.uint64), np.asarray(expected).view(np.uint64))
        changed = self.data.copy()
        changed.loc[0, "I_norm"] = np.nextafter(changed.loc[0, "I_norm"], np.inf)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "changed.csv"
            changed.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "changes coordinates"):
                validate_mapping(load(path), self.data.drop(columns="bit_label"))

    def test_receiver_operation_counts(self):
        expected = {
            "brute_force": (64, 32, 64, 31),
            "grouped": (36, 4, 36, 31),
            "independent_iq": (12, 0, 12, 10),
        }
        counts = receiver_operation_counts(self.points, "Rectangular")
        for row in counts:
            actual = tuple(row[key] for key in ("subtractions", "additions", "multiplications",
                                                "comparisons"))
            self.assertEqual(actual, expected[row["receiver"]])
        self.assertEqual(len(counts), 6)
        result = receiver_metrics("Rectangular", self.raw, self.points,
                                  np.array([[0., 0.], *self.points]))
        self.assertLessEqual(result["independent_index_mismatches"], result["tie_samples"])

    def test_ml_cells_match_inequalities_and_cover_plot(self):
        for name, group in self.data.groupby("scheme"):
            with self.subTest(scheme=name):
                points = group[["I_norm", "Q_norm"]].to_numpy()
                area = 0
                for index, cell in enumerate(ml_cells(points)):
                    self.assertGreaterEqual(len(cell), 3)
                    dist = np.sum((cell[:, None] - points)**2, axis=2)
                    self.assertTrue(np.all(dist[:, index] <= dist.min(axis=1) + 1e-12))
                    x, y = cell.T
                    area += (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2
                self.assertAlmostEqual(area, 16)

    def test_frame_guards_and_delay(self):
        rng = np.random.default_rng(12)
        symbols = rng.normal(size=32) + 1j * rng.normal(size=32)
        sps, guard = 8, 8
        taps = rrc(0.35, sps, 10)
        zero_inserted = np.zeros(len(symbols) * sps, dtype=complex)
        zero_inserted[::sps] = symbols
        full = np.convolve(zero_inserted, taps)
        start = guard * sps + (len(taps) - 1) // 2
        measured = frame_waveform(symbols, taps, sps, guard)
        self.assertEqual(len(measured), (len(symbols) - 2 * guard) * sps)
        np.testing.assert_allclose(measured, full[start:start + len(measured)], atol=1e-14)
        padded = np.r_[100 + 100j, symbols, -100 - 100j]
        np.testing.assert_allclose(frame_waveform(padded, taps, sps, guard + 1), measured)
        with self.assertRaisesRegex(ValueError, "enough guard"):
            frame_waveform(symbols, taps, sps, 4)

    def test_rrc_and_strict_ccdf(self):
        for beta in (0, 0.25, 0.35):
            taps = rrc(beta, 8, 10)
            self.assertEqual(len(taps), 81)
            np.testing.assert_allclose(taps, taps[::-1])
            self.assertAlmostEqual(np.dot(taps, taps), 1)
        thresholds, probability = empirical_ccdf(np.array([2., 2., 3., 4.]))
        np.testing.assert_array_equal(thresholds, [2., 3., 4.])
        np.testing.assert_array_equal(probability, [0.5, 0.25, 0.0])
