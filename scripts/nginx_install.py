# Copyright (c) 2026 Athena Decisions Systems SAS.
"""Put the relay and resident Medley locations into the nginx site file.

    python3 scripts/nginx_install.py SITE CONF OUT

Reads the site file SITE and the part of CONF (nginx/hearts-apps-location.conf) between its
"# BEGIN hearts-medley" and "# END hearts-medley" markers, and writes to OUT the site file with
that part just before its `location ^~ /hearts/ {` line, so in the same server block.  A copy
already there between the same markers is replaced, so running it again updates it.
./hearts.sh nginx-install runs this, then installs OUT, checks it with nginx -t and reloads.
"""
import re
import sys

PART = re.compile(r"^[ \t]*# BEGIN hearts-medley.*?^[ \t]*# END hearts-medley[^\n]*\n", re.S | re.M)
ANCHOR = re.compile(r"^[ \t]*location\s+\^~\s+/hearts/\s*\{", re.M)


def install(site_text, conf_text):
    """The new site text, and whether an earlier copy was replaced."""
    part = PART.search(conf_text)
    if not part:
        raise SystemExit("no BEGIN/END hearts-medley markers in the location file")
    # The earlier copy goes with the blank line inserted after it, so a rerun gives the same file.
    site_text, replaced = re.subn(PART.pattern + r"\n?", "", site_text, flags=re.S | re.M)
    if re.search(r"location\s+\^~\s+/hearts/(hnet|medley)/", site_text):
        raise SystemExit("the site already has /hearts/hnet/ or /hearts/medley/ locations outside the "
                         "markers (pasted by hand?): remove them, then run this again")
    anchor = ANCHOR.search(site_text)
    if not anchor:
        raise SystemExit("no `location ^~ /hearts/ {` in the site file, so no server block to add to: "
                         "paste nginx/hearts-apps-location.conf into the apps.athenadecisions.com "
                         "server block by hand")
    new = site_text[:anchor.start()] + part.group(0) + "\n" + site_text[anchor.start():]
    return new, bool(replaced)


if __name__ == "__main__":
    site, conf, out = sys.argv[1:4]
    text, replaced = install(open(site).read(), open(conf).read())
    with open(out, "w") as f:
        f.write(text)
    print(("replaced" if replaced else "added") + " the relay and resident Medley locations")
