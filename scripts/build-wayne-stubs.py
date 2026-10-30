#!/usr/bin/env python3
"""Build the placeholder board hooks the PMGR nub calls.

The nub publishes the ApplePMGRNub service AMFI waits for and then calls the
board's eMMC, input, power and DSP entry points. Those drivers are not ported
yet, so this archive supplies empty definitions (kits/<board>/wayne-board-stubs.c)
and the kernel link succeeds. Run it as a [kernel] archives entry.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/wayne-board-stubs'
SOURCE = ROOT / 'kits/wayne/wayne-board-stubs.c'


def tool(*names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit(f'missing tool: {" or ".join(names)}')


def main():
    if not SOURCE.is_file():
        raise SystemExit(f'{SOURCE} missing')
    OUT.mkdir(parents=True, exist_ok=True)
    obj = OUT / 'wayne-board-stubs.o'
    archive = OUT / 'libWayneBoardStubs.a'
    clang = tool('clang')
    command = [clang, '-target', 'arm64-apple-ios17.0', '-O2', '-c', str(SOURCE), '-o', str(obj)]
    sdk = os.environ.get('SDKROOT')
    if sdk:
        command[1:1] = ['-isysroot', sdk]
    subprocess.run(command, check=True)
    ar = tool('llvm-ar', 'ar')
    archive.unlink(missing_ok=True)
    subprocess.run([ar, 'rcs', str(archive), str(obj)], check=True)
    print(f'stubs: {archive} ({archive.stat().st_size} B)')


if __name__ == '__main__':
    sys.exit(main())
