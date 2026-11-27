import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.analyze import (
    constellation_metrics,
    empirical_ccdf,
    load,
    receiver_metrics,
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

    def test_rrc_and_strict_ccdf(self):
        for beta in (0, 0.25, 0.35):
            taps = rrc(beta, 8, 10)
            self.assertEqual(len(taps), 81)
            np.testing.assert_allclose(taps, taps[::-1])
            self.assertAlmostEqual(np.dot(taps, taps), 1)
        thresholds, probability = empirical_ccdf(np.array([2., 2., 3., 4.]))
        np.testing.assert_array_equal(thresholds, [2., 3., 4.])
        np.testing.assert_array_equal(probability, [0.5, 0.25, 0.0])
