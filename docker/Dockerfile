# Headless Medley Interlisp (Maiko + Xvfb) for scripted testing of HEARTS.
#
# Runs the same Medley release we play on (260810) against a virtual X display, so
# Interlisp forms -- including ones that open windows -- can be evaluated from a script,
# their output captured to a file, and the screen optionally snapshotted to a PNG.
#
#   docker build -t hearts-medley docker/          (or: tools/medley-headless --build)
#   tools/medley-headless path/to/script.lisp      (see docker/README.md)
#
# The Medley "full" release tarball bundles Maiko (the VM) and the loadups (sysouts),
# so nothing is compiled here.  LOOPS (Xerox's Lisp Object-Oriented Programming System)
# is not part of Medley proper; it comes from github.com/Interlisp/loops, pinned below.

FROM debian:bookworm-slim

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

# LOOPS.
RUN git clone https://github.com/Interlisp/loops.git /opt/loops \
 && if [ "${LOOPS_COMMIT}" != "HEAD" ]; then git -C /opt/loops checkout -q "${LOOPS_COMMIT}"; fi \
 && git -C /opt/loops log -1 --format='LOOPS %H %cd' \
 && rm -rf /opt/loops/.git

COPY harness.lisp /usr/local/share/hearts/harness.lisp
COPY medley-run /usr/local/bin/medley-run
RUN chmod +x /usr/local/bin/medley-run

ENV MEDLEY_HOME=/opt/medley-full \
    LOOPSDIR=/opt/loops

WORKDIR /hearts
ENTRYPOINT ["/usr/local/bin/medley-run"]
