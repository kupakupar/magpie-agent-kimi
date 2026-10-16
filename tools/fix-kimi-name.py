#!/usr/bin/env python3
"""Repair the legacy Bun install alias without reinstalling or changing accounts."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

OLD = 'magpie-agent-kimi'
NEW = 'Kimi'


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON keys; leave this file for manual review')
        result[key] = value
    return result


def read_json(raw, jsonc=False):
    text = raw.decode('utf-8-sig')
    if jsonc:
        # Strip comments and trailing commas only outside JSON strings.
        out, i = [], 0
        while i < len(text):
            if text[i] == '"':
                end = i + 1
                while end < len(text):
                    if text[end] == '\\':
                        end += 2
                    elif text[end] == '"':
                        end += 1
                        break
                    else:
                        end += 1
                out.append(text[i:end])
                i = end
            elif text.startswith('//', i):
                end = text.find('\n', i)
                i = len(text) if end < 0 else end
            elif text.startswith('/*', i):
                end = text.find('*/', i + 2)
                if end < 0:
                    raise ValueError('invalid lockfile comment')
                out.append(' ')
                i = end + 2
            else:
                out.append(text[i])
                i += 1
        text = ''.join(out)
        out, i, quoted = [], 0, False
        while i < len(text):
            char = text[i]
            if quoted and char == '\\':
                out.append(text[i:i + 2])
                i += 2
                continue
            if char == '"':
                quoted = not quoted
            if not quoted and char == ',':
                next_char = i + 1
                while next_char < len(text) and text[next_char].isspace():
                    next_char += 1
                if next_char < len(text) and text[next_char] in '}]':
                    i += 1
                    continue
            out.append(char)
            i += 1
        text = ''.join(out)
    return json.loads(text, object_pairs_hook=unique)


def atomic(file, raw):
    temp = file.with_name(file.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, file)
    finally:
        if temp.exists():
            temp.unlink()


def ensure_idle():
    parent = Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')) if sys.platform == 'win32' else (
        Path.home() / 'Library/Application Support' if sys.platform == 'darwin' else Path.home() / '.config')
    runner = parent / 'kimi-desktop/daimon-share/daimon/agents/main/runner.state.json'
    if runner.exists():
        doc = read_json(runner.read_bytes())
        count = lambda value: len(value) if isinstance(value, list) else int(value or 0)
        if count(doc.get('activeKernelTurns')) + count(doc.get('activeKernelToolCalls')):
            raise ValueError('Kimi has an active task; run again after that task finishes')


def migrate(directory):
    root = Path(directory).expanduser().resolve()
    plugins = root / 'plugins'
    manifest_file, lock_file = plugins / 'package.json', plugins / 'bun.lock'
    manifest_raw, lock_raw = manifest_file.read_bytes(), lock_file.read_bytes()
    manifest = read_json(manifest_raw)
    dependencies = manifest.get('dependencies', {})
    if OLD not in dependencies:
        if NEW in dependencies:
            return {'changed': False, 'name': NEW, 'message': 'Already repaired'}
        raise ValueError('legacy Kimi dependency not found')
    if NEW in dependencies:
        raise ValueError('both aliases exist; preserve them for manual review')
    spec = dependencies[OLD]
    if not isinstance(spec, str) or spec.split('#')[0].lower() != 'github:kupakupar/magpie-agent-kimi':
        raise ValueError('unexpected Kimi repository; no files changed')
    lock = read_json(lock_raw, jsonc=True)
    locked_deps = lock['workspaces']['']['dependencies']
    packages = lock['packages']
    if locked_deps.get(OLD) != spec or NEW in locked_deps or NEW in packages or OLD not in packages:
        raise ValueError('manifest and lockfile disagree; no files changed')
    resolved = packages[OLD]
    if not isinstance(resolved, list) or not resolved or not isinstance(resolved[0], str):
        raise ValueError('unsupported Bun lock record')
    if resolved[0].startswith(OLD + '@'):
        resolved[0] = NEW + resolved[0][len(OLD):]
    elif not resolved[0].startswith(NEW + '@'):
        raise ValueError('unexpected Bun package identity')
    modules = (plugins / 'node_modules').resolve()
    old_dir, new_dir = modules / OLD, modules / NEW
    if old_dir.parent.resolve() != modules or new_dir.parent.resolve() != modules:
        raise ValueError('module path is outside the plugin directory')
    if not old_dir.is_dir() or new_dir.exists() or new_dir.is_symlink():
        raise ValueError('unexpected module folders; no files changed')
    installed = read_json((old_dir / 'package.json').read_bytes())
    if installed.get('name') != NEW:
        raise ValueError('update the existing Kimi plugin to 0.0.5 or newer first')
    ensure_idle()
    dependencies[NEW] = dependencies.pop(OLD)
    locked_deps[NEW] = locked_deps.pop(OLD)
    packages[NEW] = packages.pop(OLD)
    changes = [(manifest_file, manifest_raw, manifest), (lock_file, lock_raw, lock)]
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    backup = root / 'backups' / ('kimi-name-' + stamp)
    backup.mkdir(parents=True, mode=0o700)
    for file, _, _ in changes:
        shutil.copy2(file, backup / file.name)
    for file, raw, _ in changes:
        if file.read_bytes() != raw:
            raise ValueError('plugin installation changed meanwhile; run again later')
    written, moved = [], False
    try:
        os.rename(old_dir, new_dir)
        moved = True
        for file, before, document in changes:
            if file.read_bytes() != before:
                raise ValueError('plugin installation changed meanwhile')
            after = (json.dumps(document, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            atomic(file, after)
            written.append((file, before, after))
    except Exception:
        for file, before, after in reversed(written):
            if file.read_bytes() == after:
                atomic(file, before)
        if moved and new_dir.exists() and not old_dir.exists():
            os.rename(new_dir, old_dir)
        raise
    return {'changed': True, 'name': NEW, 'version': installed.get('version'),
            'backup': str(backup), 'message': 'Refresh the Magpie plugins page'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', default=str(Path.home() / '.config/magpie'), help='Magpie configuration directory')
    args = parser.parse_args()
    try:
        print(json.dumps(migrate(args.directory), ensure_ascii=True))
    except Exception as error:
        print('Kimi name repair stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
