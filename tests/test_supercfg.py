from unittest import TestCase

from supercfg import Cfg


class TestCfg(TestCase):
    def test_0(self):
        cfg = Cfg.parse('cfg/test/a.cfg')
        self.assertEqual(cfg['class2::name2/x'], cfg['class2::name2/y'])

    def test_1(self):
        cfg = Cfg.parse('cfg/test/a.cfg')
        self.assertEqual([0, [[1, 0.1, [True, [1, 2]]], ['x', 44.3]]], cfg['class2::name2/z'])

    def test_2(self):
        cfg = Cfg.parse('cfg/test/a.cfg')
        sect = cfg['class2::name2']
        self.assertEqual([0, [[1, 0.1, [True, [1, 2]]], ['x', 44.3]]], sect.z)
