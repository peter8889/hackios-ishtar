#!/usr/bin/env python3
"""Lay a phone's own UEFI firmware volume out as the binary tree an EDK2 platform expects.

usage: ffs-extract.py IMAGE OUTDIR [--fv-offset 0x1000]

For every FFS file of the volume this writes, under OUTDIR:

    <Name>/<Name>.efi     the driver's PE32 section, byte for byte
    <Name>/<Name>.inf     a binary INF that names it (BASE_NAME, FILE_GUID, MODULE_TYPE)

and, for files that carry data rather than code, `RawFiles/<Name>` (the panel XMLs are these).

The MODULE_TYPE comes from the FFS file type: 0x07 DXE_DRIVER, 0x09 DXE_RUNTIME_DRIVER,
0x0B DXE_SMM_DRIVER, 0x0D SMM_CORE; everything else is written as DXE_DRIVER, which is what the
vendor's DXE drivers are. Reads only; nothing is written back to the image.
"""
import argparse
import os
import re
import shutil
import sys

import uefi_firmware

FFS_TYPE = {
    0x01: "SECURITY_CORE", 0x02: "PEI_CORE", 0x03: "DXE_CORE", 0x04: "PEIM",
    0x05: "DRIVER", 0x06: "COMBINED_PEIM_DRIVER", 0x07: "DXE_DRIVER",
    0x08: "DXE_SAL_DRIVER", 0x09: "DXE_RUNTIME_DRIVER", 0x0A: "DXE_SAL", 0x0B: "DXE_SMM_DRIVER",
    0x0C: "SMM_CORE", 0x0D: "MM_STANDALONE", 0x0E: "MM_CORE_STANDALONE",
}


def guid_text(raw):
    if isinstance(raw, str):
        return raw.upper()
    b = bytes(raw)
    if len(b) != 16:
        return "00000000-0000-0000-0000-000000000000"
    return "%08X-%04X-%04X-%s-%s" % (
        int.from_bytes(b[0:4], "little"), int.from_bytes(b[4:6], "little"),
        int.from_bytes(b[6:8], "little"), b[8:10].hex().upper(), b[10:16].hex().upper())


def collect_files(obj, acc):
    for item in getattr(obj, "objects", []) or []:
        if type(item).__name__ == "FirmwareFile":
            acc.append(item)
        collect_files(item, acc)


def section_kind(sec):
    return (getattr(sec, "attrs", {}) or {}).get("type_name", "")


def section_data(sec):
    for name in ("data", "content"):
        v = getattr(sec, name, None)
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
    return b""


def ui_name(sec):
    data = section_data(sec)
    for enc in ("utf-16-le", "utf-8"):
        try:
            text = data.decode(enc, "ignore")
        except Exception:
            continue
        text = text.replace("\x00", "").strip()
        if text and text.isprintable():
            return text
    return ""


def safe(name):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return name or "unnamed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("outdir")
    ap.add_argument("--fv-offset", default="0x1000")
    args = ap.parse_args()

    blob = open(args.image, "rb").read()[int(args.fv_offset, 0):]
    tree = uefi_firmware.AutoParser(blob).parse()
    files = []
    collect_files(tree, files)

    if os.path.isdir(args.outdir):
        shutil.rmtree(args.outdir)
    os.makedirs(os.path.join(args.outdir, "RawFiles"), exist_ok=True)

    drivers = raws = 0
    for f in files:
        name = ""
        pe32 = b""
        raw = b""
        depex = b""
        for sec in getattr(f, "objects", []) or []:
            kind = section_kind(sec)
            if kind == "User interface name":
                name = name or ui_name(sec)
            elif kind == "PE32 image":
                pe32 = section_data(sec)
            elif kind == "DXE dependency expression" and not depex:
                depex = section_data(sec)
            elif kind == "Raw" and not raw:
                raw = section_data(sec)
        if not name:
            name = "File_" + guid_text(getattr(f, "guid", b""))[:8]

        if pe32:
            d = os.path.join(args.outdir, safe(name))
            os.makedirs(d, exist_ok=True)
            base = safe(name)
            open(os.path.join(d, base + ".efi"), "wb").write(pe32)
            if depex:
                open(os.path.join(d, base + ".depex"), "wb").write(depex)
            ftype = (getattr(f, "attrs", {}) or {}).get("type")
            mtype = FFS_TYPE.get(ftype, "DXE_DRIVER")
            inf = (
                "[Defines]\n"
                "  INF_VERSION    = 0x00010005\n"
                f"  BASE_NAME      = {base}\n"
                f"  FILE_GUID      = {guid_text(getattr(f, 'guid', b''))}\n"
                f"  MODULE_TYPE    = {mtype}\n"
                "  VERSION_STRING = 1.0\n"
                "\n[Binaries]\n"
                f"  PE32|{base}.efi|true\n"
            )
            open(os.path.join(d, base + ".inf"), "w", encoding="utf-8", newline="\n").write(inf)
            drivers += 1
        elif raw:
            stem = safe(name)
            if raw.lstrip()[:1] == b"<" and not stem.lower().endswith(".xml"):
                stem += ".xml"
            open(os.path.join(args.outdir, "RawFiles", stem), "wb").write(raw)
            raws += 1

    print(f"{len(files)} FFS files: {drivers} drivers, {raws} raw files -> {args.outdir}")


if __name__ == "__main__":
    sys.exit(main())
