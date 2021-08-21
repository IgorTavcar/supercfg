import configparser
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from typing import Union

_INT_PATTERN = re.compile(r'^([0-9_]+)$')
_INT_EXP_PATTERN = re.compile(r'^([0-9_]+e[0-9_]+)$')
_FLOAT_EXP_PATTERN = re.compile(r'^([0-9_]+e-[0-9_]+)$')
_FLOAT_PATTERN = re.compile(r'^[0-9_]*\.[0-9_]*$')
_BOOL_PATTERN = re.compile(r'^(true|false)$')
_LIST_PATTERN = re.compile(r'^\(([^)]+)\)$')
_QUOTED_PATTERN = re.compile(r"'([^']*)'|\"([^\"]*)\"")
_RE_PATTERN = re.compile(r"pattern:(.+)")
_SECT_PATTERN = re.compile(r"(.+)::(.+)")


class Cfg:
    def __init__(self, path, parser, supports_properties: bool = True):
        self._path = path
        self._parser = parser
        self._sections = None
        self._supports_properties = supports_properties

    @property
    def path(self) -> str:
        return self._path

    @property
    def dir(self) -> str:
        return str(Path(self._path).parent)

    @property
    def parser(self) -> configparser.ConfigParser:
        return self._parser

    @property
    def sections(self):
        if self._sections is not None:
            return self._sections

        self._sections = self._parse_sections()
        self._resolve_sect_refs()

        if self._supports_properties:
            self._set_sect_properties()

        return self._sections

    def options(self, section: str):
        return self.sections[section]

    def parse_other_cfg(self, name):
        file = "{0}.cfg".format(os.path.join(self.dir, name))
        if file == self._path:
            return None

        if os.path.exists(file):
            return Cfg.parse(file)

        return None

    @staticmethod
    def parse(path: str):
        cfg = configparser.ConfigParser()
        cfg.read(path)
        return Cfg(path, cfg)

    #

    def __getitem__(self, item):
        path = item.split('/')
        if len(path) == 1:
            return self.sections[path[0]]
        return self._value_at(None, path)

    def __str__(self):
        return self._sections if self._sections is not None else "Cfg[...]"

    #

    def _parse_sections(self):
        build = {}
        for name in self._parser.sections():
            sect = Section.parse(self, name)
            build['{}::{}'.format(sect.clazz, sect.name)] = sect
        return build

    def _resolve_sect_refs(self):
        for _, sect in self._sections.items():
            sect.resolve_refs()

    def _set_sect_properties(self):
        for _, sect in self._sections.items():
            sect.set_properties()

    def _value_at(self, section, path: [str]):
        if len(path) == 0:
            return section
        if section is None:
            if path[0] not in self.sections:
                raise Exception('no such section: {}'.format(path[0]))
            section = self.sections[path[0]]
            return self._value_at(section, list(path[1:]))

        if section[path[0]] is None:
            raise Exception('no such option: {}, in: {}'.format(path[0], section))
        value = section[path[0]]
        if isinstance(value, Section):
            return self._value_at(value, list(path[1:]))
        if len(path) > 1:
            raise Exception('illegal path: {}, in: {}'.format(path, section))
        return value


@dataclass
class _Ref:
    cfg: Cfg = None
    path: str = None


@dataclass
class Section:
    clazz: str = None
    name: str = None
    fields: dict = None

    def __getitem__(self, item):
        path = item.split('/')
        if len(path) == 1:
            if item == 'clazz':
                return self.clazz
            if item == 'name':
                return self.name
            if item not in self.fields:
                return None
            return self.fields[item]
        else:
            ref = self[path[0]]
            if isinstance(ref, Section):
                return ref['/'.join(path[1:])]
            return None

    def get(self, key: str, default_value):
        return self[key] if self[key] is not None else default_value

    def resolve_refs(self):
        for field, value in self.fields.copy().items():
            if isinstance(value, _Ref):
                self.fields[field] = value.cfg[value.path]
            elif isinstance(value, list):
                for i, value2 in enumerate(value.copy()):
                    if isinstance(value2, _Ref):
                        value[i] = value2.cfg[value2.path]
                    elif isinstance(value2, Section):
                        value2.resolve_refs()
            elif isinstance(value, Section):
                value.resolve_refs()

    def set_properties(self):
        for field, value in self.fields.items():
            if isinstance(value, Section):
                value.set_properties()
            setattr(self, field, value) # <-- punch line

    @staticmethod
    def parse(cfg: Cfg, key: str):
        parser = cfg.parser
        if key not in parser:
            raise Exception("no such section: {}".format(key))

        sect = parser[key]

        build = {}

        domain, name = Section._split_at_2colons(key)
        if name is None:
            raise Exception("wrong section identifier: {}".format(key))

        for key in sorted(sect.keys()):
            value = sect[key].strip()
            if value in parser:
                build[key] = Section.parse(cfg, value)
                continue
            m = re.match(_QUOTED_PATTERN, value)
            if m:
                build[key] = m.group(1) if m.group(1) is not None else m.group(2)
                continue
            m = re.match(_RE_PATTERN, value)
            if m:
                build[key] = re.compile(m.group(1))
                continue
            if re.match(_INT_PATTERN, value):
                build[key] = int(value)
                continue
            if re.match(_INT_EXP_PATTERN, value):
                build[key] = int(float(value))
                continue
            if re.match(_FLOAT_PATTERN, value):
                build[key] = float(value)
                continue
            if re.match(_FLOAT_EXP_PATTERN, value):
                build[key] = float(value)
                continue
            if re.match(_BOOL_PATTERN, value):
                build[key] = _bool_value(value)
                continue
            m = re.match(_LIST_PATTERN, value)
            if m:
                build2 = []
                for item in m.group(1).split(','):
                    value2 = item.strip()
                    if value2 == 'None':
                        build2.append(None)
                        continue
                    m = re.match(_QUOTED_PATTERN, value2)
                    if m:
                        build2.append(m.group(1))
                        continue
                    if re.match(_INT_PATTERN, value2):
                        build2.append(int(value2))
                        continue
                    if re.match(_INT_EXP_PATTERN, value2):
                        build2.append(int(float(value)))
                        continue
                    if re.match(_FLOAT_PATTERN, value2):
                        build2.append(float(value2))
                        continue
                    if re.match(_FLOAT_EXP_PATTERN, value2):
                        build2.append(float(value2))
                        continue
                    if re.match(_BOOL_PATTERN, value2):
                        build2.append(_bool_value(value2))
                        continue
                    ref = Section._reference(cfg, value2)
                    if ref is not None:
                        build2.append(ref)
                    else:
                        build2.append(value2)
                build[key] = build2
                continue
            ref = Section._reference(cfg, value)
            if ref is not None:
                build[key] = ref
                continue
            build[key] = value
        return Section(domain, name, build)

    @staticmethod
    def _reference(cfg: Cfg, qualifier: str):
        # qualifier example: dataset::delo_articles-64/layout/tokenizer/vocab_size@delo_articles
        clazz, q = Section._split_at_2colons(qualifier)
        if q is None:
            return None

        split_at_monkey = Section._split_at_monkey(q)
        if split_at_monkey is not None:
            path, cfg_name = split_at_monkey
            cfg2 = cfg.parse_other_cfg(cfg_name)
            if cfg2 is not None:
                return Section._reference(cfg2, "{}::{}".format(clazz, path))
            raise Exception("no such cfg: {}.cfg, from: {}, at: {}".format(cfg_name, qualifier, cfg.dir))

        return _Ref(cfg, qualifier)

    @staticmethod
    def _split_at_2colons(key: str) -> (str, str):
        parts = key.split('::')
        if len(parts) == 1:
            return parts[0].strip(), None

        if len(parts) != 2:
            raise Exception('illegal key: {}'.format(key))

        return parts[0].strip(), parts[1].strip()

    @staticmethod
    def _split_at_monkey(key: str) -> Union[None, Tuple[str, str]]:
        parts = key.split('@')
        if len(parts) != 2:
            return None
        return parts[0].strip(), parts[1].strip()


def _bool_value(token: Union[None, str], default=False) -> bool:
    if token is None:
        return default
    return token.lower() == 'true'
