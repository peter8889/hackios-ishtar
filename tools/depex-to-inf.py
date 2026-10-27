#!/usr/bin/env python3
"""Turn a compiled DXE dependency expression back into an INF [Depex] expression.

usage: depex-to-inf.py BINARIES_DIR

EDK2's FDF has no DEPEX section -- the dependency expression of a module comes from its INF. A
module shipped as a prebuilt PE32 loses the one the vendor compiled into the firmware, which
leaves the dispatcher free to start it before the protocols it needs exist. The binary format is
a small stack language (PI spec, DXE Dependency Expression), so it converts back exactly:

    0x00 BEFORE  0x01 AFTER  0x02 PUSH <guid>  0x03 AND  0x04 OR  0x05 NOT
    0x06 END     0x07 TRUE   0x08 FALSE        0x09 SOR <guid>

The expression is appended to each module's INF as a [Depex] section.
"""
import os
import sys

OPS = {0x00: "BEFORE", 0x01: "AFTER", 0x03: "AND", 0x04: "OR", 0x05: "NOT",
       0x06: "END", 0x07: "TRUE", 0x08: "FALSE"}


def guid_text(b):
    return "%08X-%04X-%04X-%s-%s" % (
        int.from_bytes(b[0:4], "little"), int.from_bytes(b[4:6], "little"),
        int.from_bytes(b[6:8], "little"), b[8:10].hex().upper(), b[10:16].hex().upper())


def expression(data):
    out, i = [], 0
    while i < len(data):
        op = data[i]
        if op == 0x02:
            if i + 17 > len(data):
                break
            out.append(guid_text(data[i + 1:i + 17]))
            i += 17
        elif op == 0x09:
            if i + 17 > len(data):
                break
            out.append(f"SOR {guid_text(data[i + 1:i + 17])}")
            i += 17
        else:
            word = OPS.get(op)
            if word is None:
                break
            if word == "END":
                break
            if word in ("BEFORE", "AFTER", "AND", "OR", "NOT", "TRUE", "FALSE"):
                out.append(word)
            i += 1
    return " ".join(out)


def main():
    root = sys.argv[1]
    done = 0
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        depex = os.path.join(d, name + ".depex")
        inf = os.path.join(d, name + ".inf")
        if not (os.path.isfile(depex) and os.path.isfile(inf)):
            continue
        expr = expression(open(depex, "rb").read())
        if not expr or expr == "END":
            continue
        text = open(inf, encoding="utf-8").read()
        if "[Depex]" in text:
            continue
        text = text.rstrip("\n") + f"\n\n[Depex]\n  {expr}\n"
        open(inf, "w", encoding="utf-8", newline="\n").write(text)
        done += 1
    print(f"{done} modules gained a [Depex]")


if __name__ == "__main__":
    main()
