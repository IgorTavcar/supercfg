from unittest import TestCase

from supercfg import Cfg


class TestCfg(TestCase):

    def test_dict(self):
        script = """
            [a::1]
            value = {f1:'a', f2:100}
        """

        cfg = Cfg.parse_string(script)
        self.assertEqual('a', cfg['a::1'].value['f1'])

    def test_complex_dict(self):
        script = """
            [a::1]
            value = {f1:'a{{\\'', f2:"b}\\"]"}
        """

        cfg = Cfg.parse_string(script)
        self.assertEqual('a{{\'', cfg['a::1'].value['f1'])
        self.assertEqual("b}\"]", cfg['a::1'].value['f2'])

    def test_complex_dict_in_array(self):
        script = """
            [a::1]
            value = [1, 2, {f1:'a{{\\'', f2:"b}\\"]"}, 4]
        """

        cfg = Cfg.parse_string(script)
        self.assertEqual('a{{\'', cfg['a::1'].value[2]['f1'])
        self.assertEqual(4, cfg['a::1'].value[3])

    def test_array_in_array_in_array(self):
        script = """
            [a::1]
            value = [1, 2, [3, [4, '\\']'], \\]], 7]
        """
        cfg = Cfg.parse_string(script)
        self.assertEqual('\']', cfg['a::1'].value[2][1][1])
        self.assertEqual(']', cfg['a::1'].value[2][2])

    def test_cross_file_inheritance(self):
        cfg = Cfg.parse('conf/test/something.cfg')

        self.assertEqual('c', cfg['A::conf'].field1[2])
        self.assertEqual("field1 is inherited, field2 is overwritten", cfg['A::conf'].field2)

        self.assertEqual(1, cfg['B::conf'].field1[0])
        self.assertEqual("field1 is inherited, field2 is overwritten", cfg['B::conf'].field2)

    def test_infile_inheritance(self):
        cfg = Cfg.parse('conf/test/something.cfg')

        self.assertEqual(3e10, cfg['X::bla'].field1['b'])
        self.assertEqual(False, cfg['X::bla'].field2)

    def test_field_reference_1(self):
        cfg = Cfg.parse('conf/test/something.cfg')

        self.assertEqual(3e10, cfg['Y::knock_knock'].derived1['b'])

    def test_field_reference_2(self):
        cfg = Cfg.parse('conf/test/something.cfg')

        self.assertEqual('c', cfg['Q::waw'].derived1[2])

    def test_types(self):
        script = """
            [q::mmm]
            field1 = 'b'
        
            [a::1]
            int_types = [1, 1e3, 2_000_000, -3000]
            float_types = [1.3, -1., 31.e-3, 22_000.33e-2]
            bool_types = [true, false, TrUe]
            string_types = [a, ha ho, 'Q::waw', 'a\\'b']
            ref_cell0 = [a, q::mmm/field1]
            ref_cell1 = {x:111, k:q::mmm/field1}
            regex_pattern = pattern:^([+-]?[0-9_]+)$
        """
        cfg = Cfg.parse_string(script)['a::1']

        expected_ints = [1, 1e3, 2_000_000, -3000]
        self.assertEqual(expected_ints, cfg.int_types)

        expected_floats = [1.3, -1., 31.e-3, 22_000.33e-2]
        self.assertEqual(expected_floats, cfg.float_types)

        expected_bools = [True, False, True]
        self.assertEqual(expected_bools, cfg.bool_types)

        expected_strings = ['a', 'ha ho', "Q::waw", "a'b"]
        self.assertEqual(expected_strings, cfg.string_types)

        self.assertEqual('b', cfg.ref_cell1['k'])

        self.assertTrue(cfg.regex_pattern.match('-22_000'))
        self.assertFalse(cfg.regex_pattern.match('-22_00x'))
