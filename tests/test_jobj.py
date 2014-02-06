import unittest

from jreport import JObj


class TestIt(unittest.TestCase):

    def test_attribute_access(self):
        jo = JObj({'a': {'b': 23}, 'c': 45})
        self.assertEqual(jo['a']['b'], 23)
        self.assertEqual(jo['c'], 45)

    def test_dotted_attribute_access(self):
        jo = JObj({'a': {'b': 23}, 'c': 45})
        self.assertEqual(jo['a.b'], 23)

    def test_basic_formatting(self):
        jo = JObj({'a':17, 'b':34})
        self.assertEqual(jo.format("{a}:{b}"), "17:34")

    def test_number_formatting(self):
        jo = JObj({'a':17, 'b':34})
        self.assertEqual(jo.format("{a:04d}:{b:-^10d}"), "0017:----34----")
        self.assertEqual(jo.format("{a:.3f}:{b:*>20e}"), "17.000:********3.400000e+01")

    def test_subobject_formatting(self):
        jo = JObj({'a': {'b': 23}, 'c': 45})
        self.assertEqual(jo.format("{a.b:5d}!"), "   23!")
