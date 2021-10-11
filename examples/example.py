from supercfg import Cfg

# file: cfg/example.cfg
"""
[a::1]
filed_a = 100_000
filed_b = [1, 2, 3]
pattern_1 = pattern:^hello: (\d)$
ref_b = b::1

[a::2]
filed_a = 30_000
filed_b = [1, 2, 5]
pattern_1 = pattern:^hello: (\d{2})$
ref_b = b::1

[b::1]
say_1 = 'all those moments will be lost in time ...'
say_2 =  c::x/somebody

[c::x]
somebody = "say something else"
"""


def main():
    cfg = Cfg.parse('cfg/example.cfg')
    a = cfg['a::1']
    print(a.ref_b.say_2)
    print(a.pattern_1.match('hello: 1') is not None)
    a = cfg['a::2']
    print(a.filed_b[:-1])
    print(a['ref_b/say_1'])
    print(a.pattern_1.match('hello:  11') is not None)


if __name__ == '__main__':
    main()
