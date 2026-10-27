#!/usr/bin/env python3
"""Turn FILE DRIVER blocks in a platform's DXE include back into INF lines."""
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()


def repl(match):
    body = match.group(0)
    name = re.search(r'SECTION UI = "([^"]+)"', body)
    if not name:
        return body
    n = name.group(1)
    return f"  INF Binaries/ishtar/{n}/{n}.inf"


out = re.sub(r"FILE DRIVER = [0-9A-F-]+ \{[^}]*\}", repl, text)
open(path, "w", encoding="utf-8", newline="\n").write(out)
print("INF lines:", out.count("INF Binaries/ishtar"))
