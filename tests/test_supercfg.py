from unittest import TestCase

from supercfg import Cfg


class TestCfg(TestCase):
    def test_access(self):
        cfg = Cfg.parse('cfg/test/test.cfg')
        self.assertEqual('gpt', cfg['dataset::delo_articles_part-edged/layout/tokenizer/target_model'])

    def test_access2(self):
        cfg = Cfg.parse('cfg/test/test2.cfg')
        self.assertEqual('gpt', cfg['trainer::minigpt_delo_articles-part/dataset/layout/tokenizer/target_model'])

    def test_access3(self):
        cfg = Cfg.parse('cfg/test/test3.cfg')
        self.assertEqual(30_000, cfg['trainer::minigpt_delo_articles-64/dataset/layout/tokenizer/vocab_size'])

    def test_xy(self):
        cfg = Cfg.parse('cfg/test/a.cfg')
        self.assertEqual(cfg['class2::name2/x'], cfg['class2::name2/y'])

    def test_z(self):
        cfg = Cfg.parse('cfg/test/a.cfg')
        self.assertEqual(cfg['class2::name2/z'], [0, [1, 0.1, True, [1, 2]]])

    def test_attrs_1(self):
        cfg = Cfg.parse('cfg/test/a.cfg')
        sect = cfg['class2::name2']
        self.assertEqual(sect.z, [0, [1, 0.1, True, [1, 2]]])

    def test_attrs_2(self):
        cfg = Cfg.parse('cfg/test/test3.cfg')
        sect = cfg['trainer::minigpt_delo_articles-64']
        self.assertEqual(sect.dataset.layout.window_step, 0.5)
