#!/usr/bin/env python3
"""Emit FDF FILE blocks for the extracted drivers, keeping their dependency expressions.

usage: gen-binary-inc.py PLATFORM_DIR BINARIES_DIR

An INF that names a prebuilt PE32 carries no [Depex], so EDK2 gives the module a TRUE dependency
and the dispatcher may start it before the protocols it needs exist. Writing the FFS entry out in
the FDF instead -- PE32 plus the DEPEX section the phone's own firmware carries -- keeps the
original dispatch order requirements. The file blocks are emitted in the order the platform's
DXE.inc lists them, and DXE.inc's `INF Binaries/...` lines are replaced by one include.
"""
import os
import re
import sys


def guid_of(inf):
    m = re.search(r"FILE_GUID\s*=\s*(\S+)", open(inf, encoding="utf-8").read())
    return m.group(1) if m else None


def main():
    plat, bindir = sys.argv[1], sys.argv[2]
    inc = os.path.join(plat, "Include", "DXE.inc")
    lines = open(inc, encoding="utf-8").read().splitlines()

    order, seen = [], set()
    for line in lines:
        m = re.match(r"\s*INF\s+Binaries/ishtar/([^/]+)/", line)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            order.append(m.group(1))
    for name in sorted(os.listdir(bindir)):
        if name not in seen and os.path.isfile(os.path.join(bindir, name, name + ".efi")):
            order.append(name)

    blocks = []
    for name in order:
        d = os.path.join(bindir, name)
        inf = os.path.join(d, name + ".inf")
        if not os.path.isfile(inf):
            continue
        guid = guid_of(inf)
        if not guid:
            continue
        body = [f"FILE DRIVER = {guid} {{",
                f"  SECTION PE32 = Binaries/ishtar/{name}/{name}.efi"]
        depex = os.path.join(d, name + ".depex")
        if os.path.isfile(depex):
            body.append(f"  SECTION DEPEX = Binaries/ishtar/{name}/{name}.depex")
        body.append(f'  SECTION UI = "{name}"')
        body.append("}")
        blocks.append("\n".join(body))

    out = os.path.join(plat, "Include", "BINARY.inc")
    open(out, "w", encoding="utf-8", newline="\n").write("\n\n".join(blocks) + "\n")

    new, done = [], False
    for line in lines:
        if re.match(r"\s*INF\s+Binaries/ishtar/", line):
            if not done:
                new.append("!include BINARY.inc")
                done = True
            continue
        new.append(line)
    open(inc, "w", encoding="utf-8", newline="\n").write("\n".join(new) + "\n")
    print(f"{len(blocks)} file blocks, {sum(1 for n in order if os.path.isfile(os.path.join(bindir, n, n + '.depex')))} with a dependency expression")


if __name__ == "__main__":
    main()
