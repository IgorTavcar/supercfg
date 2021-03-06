from supercfg import Cfg

# file: conf/example.cfg
"""
[a::template]
field_a = 99_999

[a::1(template)]
filed_b = [1, 2, 3]
pattern_1 = pattern:^hello:\s*(\d)+$
ref_b = b::1

[a::2(1)]
filed_b = [3, 2, 1]
ref_b = b::2

[b::1]
say_1 = 'all those moments will be lost in time ...'
say_2 =  c::x/somebody


[b::2(1)]
say_1 = 'other text'
say_2 =  c::x/somebody_else

[c::x]
somebody = "say something else"
somebody_else = "say the same"
"""


def main():
    cfg = Cfg.parse('conf/example.cfg')
    a1 = cfg['a::1']
    print(a1.all_fields)
    a2 = cfg['a::2']
    print(a2.pattern_1.match('hello:  11') is not None)


if __name__ == '__main__':
    main()
