import configparser
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from typing import Union

_SUPERCLASS_PATTERN = re.compile(r'^[^(]+\(([^)]+)\)')
_NONE_PATTERN = re.compile(r'None|none|NONE')
_INT_PATTERN = re.compile(r'^([0-9_]+)$')
_INT_EXP_PATTERN = re.compile(r'^([0-9_]+e[0-9_]+)$')
_FLOAT_EXP_PATTERN = re.compile(r'^([0-9_]+e-[0-9_]+)$')
_FLOAT_PATTERN = re.compile(r'^[0-9_]*\.[0-9_]*$')
_BOOL_PATTERN = re.compile(r'^(true|false)$')
_LIST_PATTERN = re.compile(r'^\[([^]]+)\]$')
_QUOTED_PATTERN = re.compile(r"'([^']*)'|\"([^\"]*)\"")
_RE_PATTERN = re.compile(r"pattern:(.+)")
_SECT_PATTERN = re.compile(r"(.+)::(.+)")


class Cfg:
    def __init__(self, path, parser):
        self._path = path
        self._parser = parser
        self._sections = None

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
        if not os.path.exists(path):
            raise Exception('no such file: {}'.format(path))
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

    def __hash__(self) -> int:
        return hash(self.path)


@dataclass
class Section:
    clazz: str = None
    name: str = None
    fields: dict = None

    _superclass_id = None
    _super = None
    _all_fields: dict = None

    def __post_init__(self):
        m = _SUPERCLASS_PATTERN.match(self.name)
        if m:
            value = m[1]
            if '::' not in value:
                self._superclass_id = self.clazz + '::' + value
            else:
                self._superclass_id = value
            self.name = self.name[:-(len(value) + 2)]

    def __getitem__(self, item):
        if isinstance(item, int):
            if item == 0:
                return 'clazz'
            if item == 1:
                return 'name'
            return list(self.all_fields.keys())[item - 2]

        path = item.split('/')
        if len(path) == 1:
            if item == 'clazz':
                return self.clazz
            if item == 'name':
                return self.name
            if item not in self.fields:
                return None
            return self.all_fields[item]
        else:
            ref = self[path[0]]
            if isinstance(ref, Section):
                return ref['/'.join(path[1:])]
            return None

    def __len__(self):
        return 2 + len(self.all_fields)

    @property
    def all_fields(self) -> dict:
        if self._all_fields:
            return self._all_fields
        if self._super:
            build = self._super.all_fields
        else:
            build = {}
        build.update(self.fields)
        self._all_fields = build
        return build

    @property
    def to_dict(self):
        build = {'name': self.name, 'clazz': self.clazz}
        for k, v in self.all_fields.items():
            if isinstance(v, Section):
                build[k] = v.to_dict
            else:
                build[k] = v
        return build

    def get(self, key: str, default_value):
        return self[key] if self[key] is not None else default_value

    def resolve_refs(self):
        if self._super and isinstance(self._super, _Ref):
            self._super = self._super.cfg[self._super.path]

        for field, value in self.fields.copy().items():
            self.fields[field] = Section._resolve_ref(value)

        self._set_properties()

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
            build[key] = Section._parse_item(cfg, value, parser)

        created = Section(domain, name, build)
        if created._superclass_id:
            created._super = Section._reference(cfg, created._superclass_id)
        return created

    @staticmethod
    def _parse_items(cfg: Cfg, items: [any], parser: configparser.ConfigParser):
        build = []
        for item in items:
            value = item.strip()
            build.append(Section._parse_item(cfg, value, parser))
        return build

    #

    @staticmethod
    def _parse_item(cfg: Cfg, value: any, parser: configparser.ConfigParser):
        if value in parser:
            return Section.parse(cfg, value)

        m = re.match(_QUOTED_PATTERN, value)
        if m:
            return m.group(1) if m.group(1) is not None else m.group(2)
        m = re.match(_RE_PATTERN, value)
        if m:
            return re.compile(m.group(1))
        if re.match(_NONE_PATTERN, value):
            return None
        if re.match(_INT_PATTERN, value):
            return int(value)
        if re.match(_INT_EXP_PATTERN, value):
            return int(float(value))
        if re.match(_FLOAT_PATTERN, value):
            return float(value)
        if re.match(_FLOAT_EXP_PATTERN, value):
            return float(value)
        if re.match(_BOOL_PATTERN, value):
            return Section._bool_value(value)
        if value.startswith('[') and value.endswith(']'):
            # todo: rewrite
            expression = value[1:-1]
            return Section._parse_items(cfg, Section._split_expression(expression), parser)
        ref = Section._reference(cfg, value)
        if ref is not None:
            return ref
        return value

    @staticmethod
    def _resolve_ref(value: any):
        if isinstance(value, _Ref):
            return Section._resolve_ref(value.cfg[value.path])
        if isinstance(value, list):
            for i, inner_value in enumerate(value.copy()):
                if isinstance(inner_value, _Ref):
                    value[i] = Section._resolve_ref(inner_value)
                elif isinstance(inner_value, list):
                    value[i] = Section._resolve_ref(inner_value)
                elif isinstance(inner_value, Section):
                    inner_value.resolve_refs()
        if isinstance(value, Section):
            value.resolve_refs()
            return value
        return value

    @staticmethod
    def _reference(cfg: Cfg, qualifier: str):
        # qualifier example: dataset::articles-64/layout/tokenizer/vocab_size@articles
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
    def _split_expression(expression: str) -> [str]:
        build = []
        item = ""
        capture_until = []
        for char in expression:
            if char == '[':
                capture_until.append(']')
            elif char == '\'' and (len(capture_until) == 0 or capture_until[-1] != '\''):
                capture_until.append('\'')
            # elif char == '{':
            #     capture_until.append('}')
            elif len(capture_until) > 0 and char == capture_until[-1]:
                capture_until.pop()
            elif len(capture_until) == 0 and char == ',':
                item = item.strip()
                if len(item) > 0:
                    build.append(item)
                    item = ""
                continue
            item += char  # capture

        item = item.strip()
        if len(item) > 0:
            build.append(item)

        return build

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

    @staticmethod
    def _bool_value(token: Union[None, str], default=False) -> bool:
        if token is None:
            return default
        return token.lower() == 'true'

    def _set_properties(self):
        for field, value in self.all_fields.items():
            if isinstance(value, Section):
                value._set_properties()
            setattr(self, field, value)  # <-- punch line

