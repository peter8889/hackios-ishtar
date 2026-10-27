#!/usr/bin/env python3
"""Rewrite an EDK2 platform's include lists to a flat `Binaries/<device>/<Name>/` layout.

usage: fix-include.py PLATFORM_DIR BINARIES_DIR

The platform package was copied from a sibling device and still names the vendor's paths
(`Binaries/<device>/QcomPkg/Drivers/TzDxe/TzDxeLA.inf`). The extraction writes one directory per
module, named by the module's UI section, so every such line is rewritten to the directory that
holds the same module; the order of the file is preserved, because DXE dispatch order matters.
Names that differ between the vendor tree and the firmware volume are matched by a table below.
"""
import os
import re
import sys

# vendor INF name -> the name the firmware volume's UI section carries, where they differ
ALIAS = {
    "chipinfodxe": "ChipInfo",
    "dalsysdxe": "DALSys",
    "haliommudxe": "HALIOMMU",
    "hwiodxe": "HWIODxeDriver",
    "i2cdxe": "I2C",
    "platforminfodxe": "PlatformInfoDxeDriver",
    "pmicdxela": "PmicDxe",
    "spidxe": "SPI",
    "spmidxe": "SPMI",
    "tlmmdxe": "DALTLMM",
    "xhcipciemulationdxe": "XhciPciEmulation",
    "glinkdxe": "GlinkDxe",
}


def resolve(name, names):
    if name in names:
        return name
    low = name.lower()
    if low in ALIAS and ALIAS[low] in names:
        return ALIAS[low]
    for n in names:
        if n.lower() == low:
            return n
    return None


def main():
    plat, bindir = sys.argv[1], sys.argv[2]
    names = {d for d in os.listdir(bindir) if os.path.isdir(os.path.join(bindir, d))}
    for inc in ("DXE.inc", "APRIORI.inc", "RAW.inc"):
        path = os.path.join(plat, "Include", inc)
        if not os.path.isfile(path):
            continue
        out, changed, unmapped = [], 0, []
        for line in open(path, encoding="utf-8", errors="replace").read().splitlines():
            m = re.match(r"(\s*)INF\s+Binaries/[^/]+/.*?/([^/]+)\.inf\s*$", line)
            if m:
                indent, name = m.group(1), m.group(2)
                real = resolve(name, names)
                if real:
                    out.append(f"{indent}INF Binaries/ishtar/{real}/{real}.inf")
                    changed += 1
                    continue
                unmapped.append(name)
            m2 = re.match(r"(\s*)SECTION\s+RAW\s*=\s*Binaries/[^/]+/(.*)$", line)
            if m2:
                indent, rest = m2.group(1), m2.group(2)
                base = os.path.basename(rest)
                if os.path.exists(os.path.join(bindir, "RawFiles", base)):
                    out.append(f"{indent}SECTION RAW = Binaries/ishtar/RawFiles/{base}")
                    changed += 1
                    continue
                unmapped.append(rest)
            out.append(line)
        open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        print(f"{inc}: {changed} lines rewritten" + (f", unmapped: {sorted(set(unmapped))}" if unmapped else ""))


if __name__ == "__main__":
    main()
