#!/usr/bin/env python3
"""Fetch every submodule of a repository at a pinned commit, from tarballs.

usage: fetch-submodules.py OWNER/REPO COMMIT DEST

git clone is throttled on this link, codeload is not, so each submodule is fetched as a tarball of
the commit the parent pins. Existing non-empty directories are left alone.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

repo, commit, dest = sys.argv[1], sys.argv[2], sys.argv[3]


def api(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "fetch-submodules"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


raw = urllib.request.urlopen(
    f"https://raw.githubusercontent.com/{repo}/{commit}/.gitmodules", timeout=60).read().decode()

blocks = re.findall(r"\[submodule \"([^\"]+)\"\]\s*\n((?:\s+\w+\s*=\s*.*\n?)+)", raw)
print(f"{len(blocks)} submodules")

for name, body in blocks:
    path = re.search(r"path\s*=\s*(\S+)", body).group(1)
    url = re.search(r"url\s*=\s*(\S+)", body).group(1)
    target = os.path.join(dest, path)
    if os.path.isdir(target) and os.listdir(target):
        print(f"skip   {path}")
        continue
    m = re.match(r"https://github\.com/([^/]+)/([^/.]+)", url)
    if not m:
        print(f"manual {path}  ({url})")
        continue
    owner, name_only = m.group(1), m.group(2)
    try:
        info = api(f"https://api.github.com/repos/{repo}/contents/{path}?ref={commit}")
        sha = info.get("sha")
    except Exception as e:
        print(f"nosha  {path}: {e}")
        continue
    if not sha:
        print(f"nosha  {path}")
        continue
    os.makedirs(target, exist_ok=True)
    tar = f"/tmp/sub_{name_only}.tar.gz"
    code = subprocess.run(["curl", "-sL", "-o", tar,
                           f"https://codeload.github.com/{owner}/{name_only}/tar.gz/{sha}"]).returncode
    if code != 0 or os.path.getsize(tar) < 1024:
        print(f"fail   {path}  (download)")
        continue
    subprocess.run(["tar", "xzf", tar, "-C", target, "--strip-components=1"], check=False)
    print(f"got    {path}  {sha[:10]}  {sum(len(f) for _, _, f in os.walk(target))} files")
