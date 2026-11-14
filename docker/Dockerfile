# Headless Medley Interlisp (Maiko + Xvfb) for scripted testing of HEARTS.
#
# Runs the same Medley release we play on (260810) against a virtual X display, so
# Interlisp forms -- including ones that open windows -- can be evaluated from a script,
# their output captured to a file, and the screen optionally snapshotted to a PNG.
#
#   docker build -t hearts-medley docker/          (or: tools/medley-headless --build)
#   tools/medley-headless path/to/script.lisp      (see docker/README.md)
#
# The Medley "full" release tarball bundles Maiko (the VM) and the loadups (sysouts).  Its
# emulators are built with no network, so the same Maiko release is rebuilt here with
# -DMAIKO_ENABLE_NETHUB and put in their place: `medley --nethub HOST:PORT:MAC` then joins an
# XNS NetHub, which is how HEARTS reaches the house (medley/hcourier.lisp).  LOOPS (Xerox's
# Lisp Object-Oriented Programming System) is not part of Medley proper; it comes from
# github.com/Interlisp/loops, pinned below.

FROM debian:bookworm-slim AS maiko
ARG MAIKO_TAG=maiko-260319-9259716e
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git build-essential clang libx11-dev pkg-config libbsd-dev bc \
 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch "${MAIKO_TAG}" https://github.com/Interlisp/maiko.git /opt/maiko-src
# Built as the release is (bin/makeright x), not with cmake: a cmake Release build of this tag
# with MAIKO_NETWORK_TYPE=NETHUB crashed at startup on linux aarch64 (2026-11-14, cause not looked for).
RUN cd /opt/maiko-src/bin \
 && ADDITIONAL_DFLAGS=-DMAIKO_ENABLE_NETHUB ./makeright x \
 && mkdir /opt/maiko-build && cp "$(dirname "$(find /opt/maiko-src -name ldex -type f)")"/lde* /opt/maiko-build/

FROM debian:bookworm-slim AS medley

ARG MEDLEY_RELEASE=260810-634d092e_260319-9259716e
ARG LOOPS_COMMIT=8508dd0d9af4b237c4f18c05d6655fefc621dfa3
ARG TARGETARCH

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git xvfb x11-apps x11-utils netpbm procps \
 && rm -rf /var/lib/apt/lists/*

# Medley + Maiko, for this container's architecture.
RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      arm64|aarch64) ARCH=aarch64 ;; \
      amd64|x86_64)  ARCH=x86_64 ;; \
      *) echo "unsupported arch ${TARGETARCH}"; exit 1 ;; \
    esac; \
    url="https://github.com/Interlisp/medley/releases/download/medley-${MEDLEY_RELEASE}/medley-full-linux-${ARCH}-${MEDLEY_RELEASE}.tgz"; \
    mkdir -p /opt/medley-full; \
    curl -fsSL "$url" | tar -xz -C /opt/medley-full; \
    ls /opt/medley-full

# The emulators with NetHub support, over the release's.
COPY --from=maiko /opt/maiko-build/ldex /opt/maiko-build/lde /tmp/nh/
RUN set -eux; d="$(dirname "$(find /opt/medley-full/maiko -name ldex -type f)")"; \
    cp /tmp/nh/ldex /tmp/nh/lde "$d/"; rm -rf /tmp/nh; "$d/ldex" -help 2>&1 | grep -i "nh-host"

# LOOPS.
RUN git clone https://github.com/Interlisp/loops.git /opt/loops \
 && if [ "${LOOPS_COMMIT}" != "HEAD" ]; then git -C /opt/loops checkout -q "${LOOPS_COMMIT}"; fi \
 && git -C /opt/loops log -1 --format='LOOPS %H %cd' \
 && rm -rf /opt/loops/.git

# Python and the Anthropic and OpenAI SDKs, for the LLM player's helper (medley/llm_player.py);
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip \
 && pip3 install --break-system-packages --no-cache-dir anthropic openai \
 && rm -rf /var/lib/apt/lists/*

ENV MEDLEY_HOME=/opt/medley-full \
    LOOPSDIR=/opt/loops

# --- The resident Medley for the demo server (docker-compose.server.yml, target "resident") ---
# Medley on a virtual display that people can watch, or control, from a browser: two VNC
# servers on the display (view-only and full) and noVNC for each.  xclip is how Medley's
# CLIPBOARD library pastes (Meta-V) and copies; autocutsel carries text between those X
# selections and the cut buffer, which is all x11vnc uses for the browser's clipboard.  docker/resident.lisp keeps
# offering players to the house, over Courier.  See docs/medley-server.md.
FROM medley AS resident
RUN apt-get update \
 && apt-get install -y --no-install-recommends x11vnc novnc websockify xclip autocutsel \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash medley
COPY resident.lisp /usr/local/share/hearts/resident.lisp
COPY resident-run /usr/local/bin/resident-run
RUN chmod +x /usr/local/bin/resident-run
USER medley
WORKDIR /home/medley
EXPOSE 6080 6081
ENTRYPOINT ["/usr/local/bin/resident-run"]

# --- The test harness: the default target, built by tools/medley-headless ---
FROM medley AS harness
COPY harness.lisp /usr/local/share/hearts/harness.lisp
COPY medley-run /usr/local/bin/medley-run
RUN chmod +x /usr/local/bin/medley-run
WORKDIR /hearts
ENTRYPOINT ["/usr/local/bin/medley-run"]
