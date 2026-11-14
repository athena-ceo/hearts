# Copyright (c) 2026 Athena Decision Systems SAS.
"""scripts/nginx_install.py: the HEARTS locations go into the right server block, once, whatever was there."""
import importlib.util
import itertools
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("nginx_install", ROOT / "scripts" / "nginx_install.py")
nginx_install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nginx_install)
CONF = (ROOT / "nginx" / "hearts-apps-location.conf").read_text()

HTTP = "server {\n    listen 80;\n    server_name apps.athenadecisions.com;\n    return 301 https://$host$request_uri;\n}\n"
OTHER = "server {\n    listen 443 ssl;\n    server_name other.example.org;\n    location / { return 404; }\n}\n"
OLD = ("    # BEGIN hearts-medley: the relay and the resident Medley\n    location ^~ /hearts/hnet/ {\n"
       "        proxy_pass http://127.0.0.1:8051/hnet/;\n    }\n    location ^~ /hearts/medley/watch/ {\n"
       "        proxy_pass http://127.0.0.1:8052/;\n    }\n    # END hearts-medley\n\n")


def https(inside="", last="}\n"):
    return ("server {\n    listen 443 ssl; # managed by Certbot\n    server_name apps.athenadecisions.com;\n"
            "    location / { proxy_pass http://127.0.0.1:3000; }  # the demos page { not a block\n"
            "    location ^~ /advent/ {\n        proxy_pass http://127.0.0.1:3040/;\n    }\n" + inside + last)


@pytest.mark.parametrize("before, after, earlier, last", itertools.product(
    ["", HTTP, OTHER], ["", HTTP + OTHER], ["", OLD], ["}\n", "    location = /x { return 204; } }\n"]))
def test_the_locations_go_into_the_https_block_once(before, after, earlier, last):
    site = before + https(earlier, last) + after
    text, replaced, where = nginx_install.install(site, CONF)
    assert replaced == bool(earlier) and "apps.athenadecisions.com" in where
    start, close = nginx_install.pick_server(text, "apps.athenadecisions.com")
    block = text[start:close]
    for path in ("= /hearts/health", "^~ /hearts/api/", "^~ /hearts/medley/watch/", "^~ /hearts/medley/control/", "^~ /hearts/ {"):
        assert block.count("location " + path) == 1 and text.count("location " + path) == 1
    assert "/hearts/hnet/" not in text and "hearts-medley:" not in text
    assert "location ^~ /advent/" in block and text.startswith(before) and text.endswith(after)
    assert [b for b in nginx_install.server_blocks(text)] and len(nginx_install.server_blocks(text)) == len(nginx_install.server_blocks(site))
    again, replaced_again, _ = nginx_install.install(text, CONF)
    assert again == text and replaced_again  # Running it again changes nothing.


def test_it_refuses_what_it_cannot_place_safely():
    with pytest.raises(SystemExit, match="outside the markers"):
        nginx_install.install(https("    location ^~ /hearts/ {\n        proxy_pass http://127.0.0.1:3050/;\n    }\n"), CONF)
    with pytest.raises(SystemExit, match="not sure which"):
        nginx_install.install(https() + https(), CONF)
    with pytest.raises(SystemExit, match="markers"):
        nginx_install.install(https(), "location /hearts/ { }")
