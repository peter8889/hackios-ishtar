#!/usr/bin/env python3
"""Inventory the FFS files of a UEFI firmware volume: one line per file.

usage: ffs-inventory.py IMAGE [FV_OFFSET]      (default offset 0x1000)

Each line: size, GUID, the name the file's UI section carries (that is the driver name in the
vendor tree), and what follows -- PE32 for a driver, RAW for data. Reads only.
"""
import sys

import uefi_firmware


def files_of(obj, acc):
    for item in getattr(obj, "objects", []) or []:
        if type(item).__name__ == "FirmwareFile":
            acc.append(item)
        files_of(item, acc)


def sections_of(obj):
    for item in getattr(obj, "objects", []) or []:
        yield item
        yield from sections_of(item)


def main():
    path = sys.argv[1]
    off = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x1000
    data = open(path, "rb").read()[off:]
    tree = uefi_firmware.AutoParser(data).parse()

    acc = []
    files_of(tree, acc)
    rows = []
    for f in acc:
        guid = getattr(f, "guid", b"")
        if isinstance(guid, bytes):
            g = guid.hex()
            guid = f"{g[0:8]}-{g[8:12]}-{g[12:16]}-{g[16:20]}-{g[20:32]}".upper()
        ui, kinds = "", []
        for s in sections_of(f):
            t = (getattr(s, "attrs", {}) or {}).get("type_name", "")
            if t == "UI":
                ui = getattr(s, "text", None) or getattr(s, "value", None) or ui
            elif t:
                kinds.append(t)
        kind = "PE32" if "PE32" in kinds else (kinds[0] if kinds else "?")
        rows.append((int(getattr(f, "size", 0) or 0), str(guid), str(ui), kind))

    rows.sort(key=lambda r: (r[3] != "PE32", r[2].lower()))
    print(f"{len(rows)} FFS files")
    for size, guid, ui, kind in rows:
        print(f"{size:>9}  {guid}  {kind:<10} {ui}")


if __name__ == "__main__":
    main()
