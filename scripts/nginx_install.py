# Copyright (c) 2026 Athena Decision Systems SAS.
"""Put the HEARTS locations (the web game and the resident Medley's screens) into the nginx site file.

    python3 scripts/nginx_install.py SITE CONF OUT [SERVER_NAME]

Reads the site file SITE and the part of CONF (nginx/hearts-apps-location.conf) between its
"# BEGIN hearts" and "# END hearts" markers, and writes to OUT the site file with that part at the
end of the server block for SERVER_NAME (apps.athenadecisions.com), the one listening on 443 when
there are several (certbot leaves a second one, on 80, that redirects).  nginx chooses a location
by its path, not its place in the file, so the end of the block is as good as anywhere.
A copy already there is replaced, so running it again updates it: one between the same markers,
or one between the "hearts-medley" markers this script used until 2026-11-14.
./hearts.sh nginx-install runs this, then installs OUT, checks it with nginx -t and reloads.
"""
import re
import sys

PART = r"^[ \t]*# BEGIN hearts\b(?!-).*?^[ \t]*# END hearts\b(?!-)[^\n]*\n"
OLD_PART = r"^[ \t]*# BEGIN hearts-medley.*?^[ \t]*# END hearts-medley[^\n]*\n"


def server_blocks(text):
    """(start, close) for each top-level `server {...}`: close is the index of its closing brace.
    Braces in comments and quoted strings don't count."""
    blocks, depth, i, start = [], 0, 0, None
    while i < len(text):
        c = text[i]
        if c == "#":
            i = text.find("\n", i)
            if i < 0:
                break
            continue
        if c in "\"'":
            j = text.find(c, i + 1)
            i = (j if j >= 0 else len(text)) + 1
            continue
        if c == "{":
            if depth == 0 and re.search(r"(^|[\s;}])server\s*$", text[:i]):
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append((start, i))
                start = None
        i += 1
    return blocks


def code(text):
    """TEXT without its comments."""
    return re.sub(r"#[^\n]*", "", text)


def pick_server(text, server_name):
    blocks = server_blocks(text)
    named = [b for b in blocks
             if re.search(r"\bserver_name\b[^;]*\b" + re.escape(server_name) + r"\b", code(text[b[0]:b[1]]))]
    if not named and len(blocks) == 1:
        named = blocks                                   # the file's only server block
    https = [b for b in named if re.search(r"\blisten\b[^;]*\b(443|ssl)\b", code(text[b[0]:b[1]]))]
    choice = https or named
    if len(choice) != 1:
        raise SystemExit(f"found {len(choice)} server blocks for {server_name} (listening on 443: "
                         f"{len(https)}), so not sure which to add to: paste the part of "
                         "nginx/hearts-apps-location.conf between its hearts markers by hand")
    return choice[0]


def install(site_text, conf_text, server_name="apps.athenadecisions.com"):
    """The new site text, whether an earlier copy was replaced, and where the part went."""
    part = re.search(PART, conf_text, re.S | re.M)
    if not part:
        raise SystemExit("no BEGIN/END hearts markers in the location file")
    # An earlier copy goes with the line ending inserted after it, so a rerun gives the same file.
    replaced = 0
    for old in (PART, OLD_PART):
        site_text, n = re.subn(old + r"\n?", "", site_text, flags=re.S | re.M)
        replaced += n
    if re.search(r"location\s+(=|\^~)?\s*/hearts/", code(site_text)):
        raise SystemExit("the site already has /hearts/ locations outside the markers (pasted by hand?): "
                         "remove them, then run this again")
    start, close = pick_server(site_text, server_name)
    if not re.search(r"\bserver_name\b[^;]*\b" + re.escape(server_name) + r"\b", code(site_text[start:close])):
        server_name = "this file's only server"
    line_start = site_text.rfind("\n", 0, close) + 1
    if site_text[line_start:close].strip():          # `... }` on one line: start a new one
        site_text = site_text[:close] + "\n" + site_text[close:]
        line_start = close + 1
    where = f"at the end of the server block for {server_name}"
    return site_text[:line_start] + part.group(0) + "\n" + site_text[line_start:], bool(replaced), where


if __name__ == "__main__":
    site, conf, out = sys.argv[1:4]
    name = sys.argv[4] if len(sys.argv) > 4 else "apps.athenadecisions.com"
    text, replaced, where = install(open(site).read(), open(conf).read(), name)
    with open(out, "w") as f:
        f.write(text)
    print(("replaced" if replaced else "added") + " the HEARTS locations, " + where)
