# Builder inspired by https://github.com/alexdmoss/distroless-python
# This is similar to al3xos/python-builder:3.10-debian11 but multiplatform (arm64+amd64)
FROM superpat7/python-builder:3.12-debian11 AS python-base

# cloudflare/cloudflared is based on gcr.io/distroless/base-debian13:nonroot (debian11 before 2025)
FROM cloudflare/cloudflared:latest AS runtime-base

# Stage the debian11 shared libraries that Python needs and the runtime image lacks, so newer
# copies already in the runtime (e.g. libz) are kept. /usr/lib/<triplet> holds them whether or
# not the runtime's /lib is merged into /usr/lib.
FROM python-base AS libs
ARG TARGETARCH
USER root
COPY --from=runtime-base /usr/lib/ /runtime/usr/lib/
RUN case "$TARGETARCH" in \
      amd64) triplet=x86_64-linux-gnu ;; \
      arm64) triplet=aarch64-linux-gnu ;; \
      *) echo "Unsupported TARGETARCH: $TARGETARCH" >&2; exit 1 ;; \
    esac \
  && mkdir -p /staging/usr/lib/$triplet \
  && for lib in libbz2.so.1.0 libcrypto.so.1.1 libexpat.so.1 libffi.so.7 liblzma.so.5 \
                libsqlite3.so.0 libssl.so.1.1 libuuid.so.1 libz.so.1; do \
       [ -e /runtime/usr/lib/$triplet/$lib ] && continue; \
       src=$(readlink -e /lib/$triplet/$lib || readlink -e /usr/lib/$triplet/$lib) \
         || { echo "Missing $lib" >&2; exit 1; }; \
       cp "$src" /staging/usr/lib/$triplet/$lib || exit 1; \
     done

FROM runtime-base

LABEL authors="pat@backblaze.com"
LABEL org.opencontainers.image.source="https://github.com/backblaze-b2-samples/b2listen"
LABEL org.opencontainers.image.description="B2listen allows you to forward Backblaze B2 Event Notifications to a service listening on a local URL"
LABEL org.opencontainers.image.licenses=MIT

# Python etc
COPY --from=python-base /usr/local/lib/ /usr/local/lib/
COPY --from=python-base /usr/local/bin/python /usr/local/bin/
COPY --from=python-base /etc/ld.so.cache /etc/

# Minimal tools for build - we'll delete them later
COPY --from=python-base /bin/echo /bin/ln /bin/rm /bin/sh /bin/chown /bin/

COPY --from=libs /staging/ /

# Need to be root to install packages and create the python user
USER root

WORKDIR /app

COPY --chown=python:python ./requirements.txt requirements.txt
COPY --chown=python:python ./pyproject.toml pyproject.toml

# Do all of this in one RUN to minimize number of layers and speed up build time
RUN echo "python:x:1000:python" >> /etc/group \
  && echo "python:x:1001:" >> /etc/group \
  && echo "python:x:1000:1001::/home/python:" >> /etc/passwd \
  && python --version \
  && ln -s /usr/local/bin/python /usr/local/bin/python3 \
  && python -m pip install --upgrade pip \
  && python -m pip install --no-cache-dir --upgrade -r requirements.txt \
  && python -m pip install -e . \
  && chown python:python -R /app \
  && rm /bin/echo /bin/ln /bin/rm /bin/sh /bin/chown

COPY --chown=python:python . .

# default to running as non-root, uid=1000
USER python

# standardise on locale, don't generate .pyc, enable tracebacks on seg faults
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

# Send the equivalent of a ctrl-c when stopping the container so app shuts down gracefully
STOPSIGNAL SIGINT

# Run the script, with the known location of cloudflared
ENTRYPOINT ["python3", "-m", "b2listen", "--cloudflared-command", "/usr/local/bin/cloudflared"]

# Print usage if no params are passed
CMD ["--help"]
