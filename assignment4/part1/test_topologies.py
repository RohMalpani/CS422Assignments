"""Structural checks for the loop-rewired Part 1 topology."""

import unittest

import numpy as np

from topologies import de_bruijn, loop_rewired_de_bruijn


CASES = [(7, 2), (7, 3), (9, 2), (9, 4), (11, 2), (11, 5),
         (13, 2), (13, 3), (13, 4), (13, 6), (16, 3), (16, 5),
         (17, 2), (17, 4), (19, 3)]


class LoopRewiringTests(unittest.TestCase):
    def test_degree_and_no_self_loops(self):
        for n, d in CASES:
            with self.subTest(n=n, d=d):
                cap = loop_rewired_de_bruijn(n, d)
                np.testing.assert_array_equal(cap.sum(axis=0), np.full(n, d))
                np.testing.assert_array_equal(cap.sum(axis=1), np.full(n, d))
                np.testing.assert_array_equal(np.diag(cap), np.zeros(n))

    def test_only_self_loops_are_replaced(self):
        for n, d in CASES:
            with self.subTest(n=n, d=d):
                original = de_bruijn(n, d)
                rewired = loop_rewired_de_bruijn(n, d)
                old_nonloop = original.copy()
                np.fill_diagonal(old_nonloop, 0)
                self.assertTrue(np.all(rewired >= old_nonloop))
                self.assertEqual(int((rewired - old_nonloop).sum()), int(np.trace(original)))

    def test_two_loop_example(self):
        cap = loop_rewired_de_bruijn(7, 2)
        self.assertEqual(cap[0, 6], 1)
        self.assertEqual(cap[6, 0], 1)


if __name__ == "__main__":
    unittest.main()
