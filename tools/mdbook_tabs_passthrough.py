#!/usr/bin/env python3
# Stand-in for the `mdbook-tabs` preprocessor that HackTricks' book.toml wants
# but which ships no prebuilt binary.  SKELETON points mdbook at this instead
# with  MDBOOK_PREPROCESSOR__TABS__COMMAND=tools/mdbook_tabs_passthrough.py
# so `run hacktricks` works without cargo / a Rust toolchain.
#
# It is not a real tab renderer: it just unwraps the `{{#tabs}}` markers so the
# ~30 pages that use them read as plain sections instead of leaking raw syntax.
import json
import re
import sys

TAB_NAME = re.compile(r'{{#tab\s+name="([^"]*)"\s*}}')
DROP = re.compile(r'{{#(?:tabs|endtab|endtabs)\s*}}')


def unwrap(md):
    if "{{#tab" not in md:
        return md
    md = TAB_NAME.sub(lambda m: "\n**{}**\n".format(m.group(1)), md)
    return DROP.sub("", md)


def walk(items):
    for it in items:
        ch = it.get("Chapter")
        if not ch:
            continue
        if isinstance(ch.get("content"), str):
            ch["content"] = unwrap(ch["content"])
        walk(ch.get("sub_items", []))


def main():
    # `supports <renderer>` probe - we handle every renderer.
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)
    context, book = json.load(sys.stdin)
    walk(book.get("sections", []))
    json.dump(book, sys.stdout)


if __name__ == "__main__":
    main()
