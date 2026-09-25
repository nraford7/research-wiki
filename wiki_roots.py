"""Resolve the research-wiki roots from the folder the skill is invoked in.

The skill is project-agnostic: it never ships a hardcoded wiki. Resolution,
walking up from the start directory (default: the current working directory)
to the filesystem root, stops at the FIRST directory that matches one of:

  1. ``.research-wiki.json`` present — explicit config, keys ``wiki`` and
     ``sources`` (paths relative to that directory, or absolute).
  2. ``wiki/index.md`` present — the project layout: wiki = ``<dir>/wiki``,
     sources = ``<dir>/deeper_research`` (if it exists).
  3. the directory itself IS a wiki (``index.md`` + ``log.md`` + ``concepts/``)
     — wiki = ``<dir>``, sources = ``<dir>/../deeper_research`` (if it exists).

No match returns ``None``: the caller must ask the user or bootstrap a new wiki
at ``<cwd>/wiki`` — never fall back to another project's wiki.

CLI: ``python3 wiki_roots.py [start_dir]`` prints JSON
``{"project": ..., "wiki": ..., "sources": ..., "via": ...}`` or exits 1.
"""
import json
import os
import sys


def _is_wiki(d):
    return (os.path.isfile(os.path.join(d, "index.md"))
            and os.path.isfile(os.path.join(d, "log.md"))
            and os.path.isdir(os.path.join(d, "concepts")))


def _abs(base, p):
    if p is None:
        return None
    p = os.path.expanduser(p)
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(base, p))


def find_roots(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        cfg = os.path.join(d, ".research-wiki.json")
        if os.path.isfile(cfg):
            with open(cfg, encoding="utf-8") as fh:
                c = json.load(fh)
            return {"project": d, "wiki": _abs(d, c.get("wiki", "wiki")),
                    "sources": _abs(d, c.get("sources")), "via": cfg}
        if os.path.isfile(os.path.join(d, "wiki", "index.md")):
            src = os.path.join(d, "deeper_research")
            return {"project": d, "wiki": os.path.join(d, "wiki"),
                    "sources": src if os.path.isdir(src) else None, "via": "wiki/index.md"}
        if _is_wiki(d):
            parent = os.path.dirname(d)
            src = os.path.join(parent, "deeper_research")
            return {"project": parent, "wiki": d,
                    "sources": src if os.path.isdir(src) else None, "via": "cwd is a wiki"}
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def default_wiki(start=None):
    """Wiki path for argparse defaults; None when no wiki is found."""
    r = find_roots(start)
    return r["wiki"] if r else None


def require_wiki(path):
    """Exit with a clear message when no --wiki was given and none was found."""
    if path:
        return path
    sys.exit("research-wiki: no wiki found from the current folder "
             f"({os.getcwd()}). Run from inside a project that has a wiki/ folder, "
             "add a .research-wiki.json, or pass --wiki <path>.")


if __name__ == "__main__":
    r = find_roots(sys.argv[1] if len(sys.argv) > 1 else None)
    if not r:
        print(json.dumps({"error": "no wiki found", "cwd": os.getcwd()}))
        sys.exit(1)
    print(json.dumps(r))
