from supercfg import Cfg

# file: cfg/example.cfg
"""
[a::1]
filed_a = 100_000
filed_b = (1, 2, 3)
ref_b = b::1

[a::2]
filed_a = 30_000
filed_b = (1, 2, 5)
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
    a = cfg['a::2']
    print(a.filed_b[:-1])
    print(a['ref_b/say_1'])


if __name__ == '__main__':
    main()
