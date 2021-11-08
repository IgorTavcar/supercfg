import configparser
import os
import re
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Tuple, Optional, Callable, AnyStr, Match, Dict, Any

_SUPERCLASS_PATTERN = re.compile(r'^[^(]+\(([^)]+)\)')
_NONE_PATTERN = re.compile(r'None|none|NONE')
_INT_PATTERN = re.compile(r'^([+-]?[0-9_]+)$')
_INT_EXP_PATTERN = re.compile(r'^([+-]?[0-9_]+e[+]?[0-9_]+)$')
_FLOAT_PATTERN = re.compile(r'^([+-]?[0-9_]*\.[0-9_]*(e[+-]?[0-9_]+)?)$')
_FLOAT_PATTERN_2 = re.compile(r'^([+-]?[0-9_]+e-[0-9_]+)$')
_BOOL_PATTERN = re.compile(r'^(true|false)$')
_QUOTED_PATTERN = re.compile(r"'(.*)'|\"(.*)\"")
_RE_PATTERN = re.compile(r"pattern:(.+)")
_SECT_PATTERN = re.compile(r"(.+)::(.+)")
_TEMPLATE_PATTERN = re.compile(r'\$\(([a-zA-Z0-9_]+)\)')
_ENUM_PATTERN = re.compile(r"enum:(.+)")


#


class Cfg:
    def __init__(self, path, parser):
        self._path = path
        self._parser = parser
        self._sections = None
        self._cached_cfgs = None

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
    def sections(self, template_resolver: Optional[Callable[[Match[AnyStr]], AnyStr]] = None):
        if self._sections is not None:
            return self._sections

        self._sections = self._parse_sections()
        self._resolve_sect_refs()
        self._resolve_templates(template_resolver)

        return self._sections

    def options(self, section: str):
        return self.sections[section]

    def parse_other_cfg(self, name, cache: bool = True):
        file = "{0}.cfg".format(os.path.join(self.dir, name))
        if file == self._path:
            return None

        if cache and self._cached_cfgs and file in self._cached_cfgs:
            return self._cached_cfgs[file]

        if os.path.exists(file):
            parsed = Cfg.parse(file)
            if cache:
                if self._cached_cfgs is None:
                    self._cached_cfgs = {}
                self._cached_cfgs[file] = parsed
            return parsed
        return None

    @staticmethod
    def parse(path: str):
        if not os.path.exists(path):
            raise Exception('no such file: {}'.format(path))
        cfg = configparser.ConfigParser()
        cfg.read(path)
        return Cfg(path, cfg)

    @staticmethod
    def parse_string(script):
        cfg = configparser.ConfigParser()
        cfg.read_string(script)
        return Cfg("tmp/{}.cfg".format(str(uuid.uuid4())), cfg)

    #

    def __getitem__(self, item):
        path = item.split('/')
        if len(path) == 1:
            qualifier = path[0]
            resolved = Section.resolve_reference(self, qualifier)
            if resolved:
                return resolved
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
            sect.resolve()

    def _resolve_templates(self, template_resolver: Optional[Callable[[Match[AnyStr]], AnyStr]]):
        for _, sect in self._sections.items():
            sect._resolve_templates(template_resolver)

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
    fields: Dict[str, Any] = None

    _superclass_id = None
    _super = None
    _all_fields: Dict[str, Any] = None

    def __post_init__(self):
        m = _SUPERCLASS_PATTERN.match(self.name)
        if m:
            value = m[1]
            if '::' not in value:
                self._superclass_id = self.clazz + '::' + value
            else:
                self._superclass_id = value
            self.name = self.name[:-(len(value) + 2)]

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name != 'name' and name != 'clazz' and name != 'fields' and not name.startswith('_'):
            self._all_fields[name] = value
            if name in self.fields:
                self.fields[name] = value

    def __setitem__(self, item, value):
        if isinstance(item, str):
            if item == 'name':
                self.name = value
            elif item == 'clazz':
                self.clazz = value
            else:
                if item in self.fields:
                    self.fields[item] = value
                self._all_fields[item] = value
                self._set_attrs()
        else:
            raise Exception("assignment not supported for: {}".format(item))

    def __getitem__(self, item):
        if self._all_fields is None:
            self.resolve()

        if isinstance(item, int):
            if item == 0:
                return 'clazz'
            if item == 1:
                return 'name'
            return list(self._all_fields.keys())[item - 2]

        path = item.split('/')
        if len(path) == 1:
            if item == 'clazz':
                return self.clazz
            if item == 'name':
                return self.name
            if item not in self._all_fields:
                return None
            return self.all_fields[item]
        else:
            ref = self[path[0]]
            if isinstance(ref, Section):
                return ref['/'.join(path[1:])]
            return None

    def __len__(self):
        return 2 + len(self._all_fields) if self._all_fields is not None else 0

    @property
    def identifier(self) -> str:
        return '{}::{}'.format(self.clazz, self.name)

    @property
    def all_fields(self) -> Dict[str, Any]:
        if self._all_fields is None:
            raise Exception('illegal state')
        return self._all_fields

    @property
    def to_dict(self):
        build = {'name': self.name, 'clazz': self.clazz}
        for k, v in self._all_fields.items():
            if isinstance(v, Section):
                build[k] = v.to_dict
            else:
                build[k] = v
        return build

    def get(self, key: str, default_value):
        return self[key] if self[key] is not None else default_value

    # inner

    def resolve(self):
        self._resolve_super()

        self._resolve_fields()

        for field, value in self._all_fields.copy().items():
            self._all_fields[field] = Section._resolve_ref(value)

        self._resolve_templates()
        self._set_attrs()

    # private

    def _resolve_fields(self):
        if self._all_fields is not None:
            return
        if self._super is not None:
            parent = self._resolve_super()
            parent._resolve_fields()
            self._all_fields = parent._all_fields.copy()
        else:
            self._all_fields = {}

        for field, value in self.fields.items():
            if field in self._all_fields:
                existed = self._all_fields[field]
                if isinstance(existed, dict):
                    value.update(existed)
            self._all_fields[field] = value

    def _resolve_templates(self, template_resolver: Optional[Callable[[Match[AnyStr]], AnyStr]] = None):
        if template_resolver is None:
            template_resolver = self._template_resolver

        for field, value in self._all_fields.copy().items():
            if isinstance(value, str):
                self._all_fields[field] = _TEMPLATE_PATTERN.sub(template_resolver, value)

    def _resolve_super(self) -> 'Section':
        if self._super and isinstance(self._super, _Ref):
            self._super = self._super.cfg[self._super.path]
            return self._resolve_super()
        return self._super

    def _set_attrs(self):
        # note: this will resolve a whole inheritance branch
        for field, value in self._all_fields.items():
            if isinstance(value, Section):
                value._set_attrs()
            setattr(self, field, value)  # <-- punch line

    # helpers

    @staticmethod
    def _template_resolver(match: Match[AnyStr]) -> str:
        template = match[1]
        if template == 'TIMESTAMP':
            return "{}".format(time.strftime("%Y%m%d_%H%M%S"))
        elif template == 'UUID':
            return str(uuid.uuid4())
        return match[0]

    @staticmethod
    def resolve_reference(cfg: Cfg, qualifier: str):
        ref = Section._reference(cfg, qualifier, only_other=True)
        if ref:
            return Section._resolve_ref(ref)
        return None

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
    def _parse_array(cfg: Cfg, items: [any], parser: configparser.ConfigParser):
        build = []
        for item in items:
            value = item.strip()
            build.append(Section._parse_item(cfg, value, parser))
        return build

    @staticmethod
    def _parse_dict(cfg: Cfg, items: [any], parser: configparser.ConfigParser):
        build = {}
        for item in items:
            kv = item.strip()
            key, value = kv.split('=>', 1)
            m = re.match(_QUOTED_PATTERN, key.strip())
            if m:
                key = Section._unescape(m.group(1)) if m.group(1) is not None else Section._unescape(m.group(2))

            build[key.strip()] = Section._parse_item(cfg, value.strip(), parser)
        return build

    @staticmethod
    def _parse_item(cfg: Cfg, value: any, parser: configparser.ConfigParser):
        if value in parser:
            return Section.parse(cfg, value)

        m = re.match(_QUOTED_PATTERN, value)
        if m:
            return Section._unescape(m.group(1)) if m.group(1) is not None else Section._unescape(m.group(2))
        m = re.match(_RE_PATTERN, value)
        if m:
            return re.compile(m.group(1))
        m = re.match(_ENUM_PATTERN, value)
        if m:
            return Section._enum_value(m.group(1))
        if re.match(_NONE_PATTERN, value):
            return None
        if re.match(_INT_PATTERN, value):
            return int(value)
        if re.match(_INT_EXP_PATTERN, value):
            return int(float(value))
        if re.match(_FLOAT_PATTERN, value):
            return float(value)
        if re.match(_FLOAT_PATTERN_2, value):
            return float(value)
        if re.match(_BOOL_PATTERN, value.lower()):
            return Section._bool_value(value)
        if value.startswith('[') and value.endswith(']'):
            # array
            expression = value[1:-1]
            return Section._parse_array(cfg, Section._split_expression(expression, check=True), parser)
        if value.startswith('{') and value.endswith('}'):
            # dictionary
            expression = value[1:-1]
            return Section._parse_dict(cfg, Section._split_expression(expression, check=True), parser)
        ref = Section._reference(cfg, value)
        if ref is not None:
            return ref
        return Section._unescape(value).strip()

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
                elif isinstance(inner_value, dict):
                    value[i] = Section._resolve_ref(inner_value)
                elif isinstance(inner_value, Section):
                    inner_value.resolve()
        elif isinstance(value, dict):
            for key, inner_value in value.items():
                if isinstance(inner_value, _Ref):
                    value[key] = Section._resolve_ref(inner_value)
                elif isinstance(inner_value, list):
                    value[key] = Section._resolve_ref(inner_value)
                elif isinstance(inner_value, dict):
                    value[key] = Section._resolve_ref(inner_value)
                elif isinstance(inner_value, Section):
                    inner_value.resolve()
        elif isinstance(value, Section):
            value.resolve()
            return value
        return value

    @staticmethod
    def _reference(cfg: Cfg, qualifier: str, only_other: bool = False) -> Optional[_Ref]:
        # qualifier example: dataset::articles-64/layout/tokenizer/vocab_size@articles
        clazz, q = Section._split_at_2colons(qualifier)
        if q is None:
            return None

        split_at_monkey = Section._split_at_monkey(q)
        if split_at_monkey:
            path, cfg_name = split_at_monkey
            cfg2 = cfg.parse_other_cfg(cfg_name)
            if cfg2 is not None:
                return Section._reference(cfg2, "{}::{}".format(clazz, path))
            raise Exception("no such cfg: {}.cfg, from: {}, at: {}".format(cfg_name, qualifier, cfg.dir))

        if only_other:
            return None

        return _Ref(cfg, qualifier)

    @staticmethod
    def _unescape(value: str) -> str:
        build = ""
        escaped = False
        for char in value:
            if char == '\\' and not escaped:
                escaped = True
                continue
            build += char
        return build

    @staticmethod
    def _split_expression(expression: str, check: bool = False) -> [str]:
        build = []
        item = ""
        capture_until = []
        escaped = ''
        quoted = False
        for char in expression:
            if char == '\\' and not escaped:
                item += char
                escaped = True
                continue
            if escaped:
                item += char
                escaped = False
                continue

            if char == '[' and not quoted:
                capture_until.append(']')
            elif char == '{' and not quoted:
                capture_until.append('}')
            elif (char == '\'' or char == '"') and not quoted:
                capture_until.append(char)
                quoted = True
            elif quoted and char == capture_until[-1]:
                quoted = False
                capture_until.pop()
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
    def _split_at_monkey(key: str) -> Optional[Tuple[str, str]]:
        parts = key.split('@')
        if len(parts) != 2:
            return None
        return parts[0].strip(), parts[1].strip()

    @staticmethod
    def _bool_value(token: Optional[str], default=False) -> bool:
        if token is None:
            return default
        return token.lower() == 'true'

    @staticmethod
    def _enum_value(value: str) -> Enum:
        parts = value.rsplit('.', 1)
        constructor = Section._constructor(parts[0])
        return constructor(parts[1])

    @staticmethod
    def _constructor(name: str):
        parts = name.split('.')
        if len(parts) == 1:
            return globals()[parts[0]]
        mod = None
        for part in parts[:-1]:
            if mod is None:
                mod = __import__(part)
            else:
                mod = getattr(mod, part)
        return getattr(mod, parts[-1])
