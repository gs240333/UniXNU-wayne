#!/usr/bin/env python3
"""Compile a board driver from kits/<board> against the captured kernel ABI.

The base tree only knows the components in its catalog, so a device repository
cannot hand its own drivers to build-arm-driver.py. This script does the same
job for one board driver: it reuses the compile command `unixnu build kernel`
captured for IOPlatformExpert.cpp, substitutes the driver source and output,
builds it, checks the object is a 64-bit arm64 / iOS 17 object, and archives it
under build/<dir>/lib<Name>.a.

Run it as a [kernel] archives entry, for example:

    build-wayne-driver.py CloverSdhci --out clover-sdhci
"""
import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='driver class name, kits/<board>/<name>.cpp')
    parser.add_argument('--out', help='output directory under build/ (default: lower-case name)')
    parser.add_argument('--source', help='source file name (default: <name>.cpp)')
    parser.add_argument('--board', default='wayne', help='package directory under kits/')
    args = parser.parse_args()

    if not RECIPE.is_file():
        raise SystemExit(f'{RECIPE} missing: the kernel compile records are not available')
    source = ROOT / 'kits' / args.board / (args.source or (args.name + '.cpp'))
    if not source.is_file():
        raise SystemExit(f'{source} missing')
    out = ROOT / 'build' / (args.out or args.name.lower())
    out.mkdir(parents=True, exist_ok=True)
    destination = out / (args.name + '.o')

    record = json.loads(RECIPE.read_text().strip().rstrip(','))
    command = []
    index = 0
    arguments = record['arguments']
    while index < len(arguments):
        value = arguments[index]
        if value == record['file']:
            command.append(str(source))
        elif value == '-o':
            command.extend(['-o', str(destination)])
            index += 1
        elif value == '-Xclang' and arguments[index + 1].startswith('-W'):
            index += 1
        elif not value.startswith('-W'):
            command.append(value)
        index += 1
    command.extend(['-Wall', '-Wextra', '-Wno-unused-parameter', '-Wno-c99-designator',
                    '-Wno-reorder-init-list', '-Wno-deprecated-enum-enum-conversion',
                    '-Wno-unnecessary-virtual-specifier', '-Wno-unused-private-field',
                    '-Wno-unused-variable', '-Wno-unused-but-set-variable',
                    '-I', str(ROOT / '.cache/xnu-work/osfmk')])
    (out / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
    result = subprocess.run(command, cwd=record['directory'], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    (out / 'compile.log').write_text(result.stdout)
    if result.returncode:
        raise SystemExit(result.stdout[-4000:])

    data = destination.read_bytes()
    magic, cpu, subtype, kind, count, size = struct.unpack_from('<6I', data)
    if (magic, cpu, subtype, kind) != (0xfeedfacf, 0x100000c, 0, 1):
        raise SystemExit(f'{args.name}: unexpected object architecture')
    archive = out / ('lib' + args.name + '.a')
    archive.unlink(missing_ok=True)
    subprocess.run(['xcrun', 'ar', 'rcs', archive, destination], check=True)
    print(f'{args.name}: {archive} ({archive.stat().st_size} B)')


if __name__ == '__main__':
    sys.exit(main())
