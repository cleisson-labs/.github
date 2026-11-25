import sys
import unittest


class InterpreterTest(unittest.TestCase):
    def test_supported_interpreter(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 11))
