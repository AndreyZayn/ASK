"""Owner-editable path profiles for the documented ASK schema subset.

Patterns match vault-relative POSIX paths: '*' matches within one segment;
'**' matches zero or more segments. Rules apply in order; later properties override earlier properties.
No filesystem access, expression evaluation, or private vocabulary is involved.
"""
from fnmatch import fnmatchcase
from functools import lru_cache


def matches(path, pattern):
    parts, pats = path.split("/"), pattern.split("/")

    @lru_cache(None)
    def walk(i, j):
        if j == len(pats):
            return i == len(parts)
        if pats[j] == "**":
            return walk(i, j + 1) or (i < len(parts) and walk(i + 1, j))
        return i < len(parts) and fnmatchcase(parts[i], pats[j]) and walk(i + 1, j + 1)

    return walk(0, 0)


def check_rules(schema, check_property, error):
    rules = schema.get('x-ask-path-rules', [])
    if not isinstance(rules, list):
        raise error('x-ask-path-rules must be an array')
    declared = set(schema['properties'])
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {'glob', 'exclude', 'required', 'optional', 'forbidden', 'properties'}:
            raise error('invalid path rule or unsupported keyword')
        patterns = [rule.get('glob')]
        for field in ('exclude', 'required', 'optional', 'forbidden'):
            values = rule.get(field, [])
            if not isinstance(values, list) or not all(isinstance(x, str) and x for x in values) or len(set(values)) != len(values):
                raise error('path rule %s must be an array of unique non-empty strings' % field)
            if field == 'exclude':
                patterns += values
            elif set(values) - declared:
                raise error('path rule %s references undeclared properties' % field)
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern or pattern.startswith('/') or '\\' in pattern or '..' in pattern.split('/'):
                raise error('path rule patterns must stay vault-relative')
        properties = rule.get('properties', {})
        if not isinstance(properties, dict) or set(properties) - declared:
            raise error('path rule properties must be declared in the base schema')
        for key, spec in properties.items():
            check_property(spec, 'path rule ' + key)
        if set(rule.get('required', [])) & (set(rule.get('optional', [])) | set(rule.get('forbidden', []))):
            raise error('path rule cannot both require and omit/forbid a property')


def for_path(schema, path):
    properties = dict(schema['properties'])
    required = set(schema.get('required', []))
    forbidden = set()
    for rule in schema.get('x-ask-path-rules', []):
        if not matches(path, rule['glob']) or any(matches(path, p) for p in rule.get('exclude', [])):
            continue
        properties.update(rule.get('properties', {}))
        required.difference_update(rule.get('optional', []))
        required.update(rule.get('required', []))
        forbidden.update(rule.get('forbidden', []))
    return properties, sorted(required), sorted(forbidden)
