#!/usr/bin/env python3
"""Bundle the target image's two original trust-cache modules for the payload.

The reference tree's build-original-system-trust.py pins the static module of
that board, so it refuses another board's extraction. This does the same two
inputs and the same output shape without the board pin:

  * Cryptex1,SystemTrustCache from the target IPSW (an IM4P; field 4 is the
    version-2 trust module),
  * the target's StaticTrustCache, staged by the workflow at
    .cache/firmware/target-volumes/static-trustcache.bin,

emitted as the version-2 bundle DarwinBoot validates (header, two offsets, then
the two modules unchanged).
"""
import plistlib
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path.cwd()
IPSW = ROOT / 'refer/iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw'
STATIC = ROOT / '.cache/firmware/target-volumes/static-trustcache.bin'


def der(data, at):
    if at + 2 > len(data):
        raise ValueError('truncated DER')
    tag, size = data[at:at + 2]
    at += 2
    if size & 128:
        count = size & 127
        if not 0 < count <= 4 or at + count > len(data):
            raise ValueError('invalid DER length')
        size = int.from_bytes(data[at:at + count], 'big')
        at += count
    if at + size > len(data):
        raise ValueError('DER exceeds the original input')
    return tag, data[at:at + size], at + size


def trust_module(name, data):
    """Return the raw version-2 module inside an IM4P wrapper, or the data itself.

    The IPSW ships both trust caches as personalized IM4P blobs whose fourth DER
    field is the module; a staged extraction may already be the bare module.
    """
    if len(data) > 4 and data[:4] != b'IM4P':
        tag, sequence, end = der(data, 0)
        fields, cursor = [], 0
        while cursor < len(sequence):
            kind, field, cursor = der(sequence, cursor)
            fields.append((kind, field))
        if (tag != 0x30 or end != len(data) or len(fields) < 4 or
                fields[0][1] != b'IM4P'):
            raise SystemExit(f'{name}: an IM4P wrapper was expected')
        data = fields[-1][1]
    if len(data) < 24:
        raise SystemExit(f'{name}: shorter than a version-2 module header')
    version = struct.unpack_from('<I', data)[0]
    entries = struct.unpack_from('<I', data, 20)[0]
    if version != 2 or len(data) != 24 + entries * 24:
        raise SystemExit(f'{name}: not a complete version-2 trust module '
                         f'(version {version}, {len(data)} bytes, {entries} entries)')
    return data, entries


def main():
    if not IPSW.is_file():
        raise SystemExit(f'{IPSW} missing: the workflow downloads the target IPSW')
    if not STATIC.is_file():
        raise SystemExit(f'{STATIC} missing: the workflow stages the static trust cache')

    with zipfile.ZipFile(IPSW) as archive:
        manifest = plistlib.loads(archive.read('BuildManifest.plist'))
        identities = [i for i in manifest['BuildIdentities']
                      if i['Info']['DeviceClass'] == 'j120ap']
        if not identities:
            raise SystemExit('the IPSW has no j120ap identity')
        entry = identities[0]['Manifest']['Cryptex1,SystemTrustCache']
        original = archive.read(entry['Info']['Path'])

    tag, sequence, end = der(original, 0)
    fields, cursor = [], 0
    while cursor < len(sequence):
        kind, data, cursor = der(sequence, cursor)
        fields.append((kind, data))
    if (tag != 0x30 or end != len(original) or len(fields) != 4 or
            fields[0][1] != b'IM4P'):
        raise SystemExit('Cryptex1,SystemTrustCache is not the expected IM4P')

    static, static_entries = trust_module('static', STATIC.read_bytes())
    system, system_entries = trust_module('system', original)

    bundle = struct.pack('<3I', 2, 12, 12 + len(static)) + static + system
    out = ROOT / 'build/wayne-trust'
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'wayne-trust.bundle'
    target.write_bytes(bundle)
    print(f'trust bundle: {target} ({len(bundle)} bytes, '
          f'{static_entries} static + {system_entries} system entries)')


if __name__ == '__main__':
    sys.exit(main())
