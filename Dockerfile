# Builder inspired by https://github.com/alexdmoss/distroless-python
# This is the same as al3xos/python-builder:3.10-debian11 but multiplatform (arm64+amd64)
FROM superpat7/python-builder:3.10-debian11 AS python-base

# cloudflare/cloudflared is based on gcr.io/distroless/base-debian11:nonroot
FROM cloudflare/cloudflared:latest
LABEL authors="pat@backblaze.com"

# Python etc
COPY --from=python-base /usr/local/lib/ /usr/local/lib/
COPY --from=python-base /usr/local/bin/python /usr/local/bin/
COPY --from=python-base /etc/ld.so.cache /etc/

# Minimal tools for build - we'll delete them later
COPY --from=python-base /bin/echo /bin/ln /bin/rm /bin/sh /bin/chown /bin/

# We can probably copy less than this, but it's difficult and time consuming to find the minimal set of libraries
COPY --from=python-base /usr/lib/ /usr/lib/
COPY --from=python-base /lib/ /lib/

# Need to be root to write to /etc
USER root

# Set up a non-root user
# Perform a quick validation that python still works whilst we have a shell
RUN echo "python:x:1000:python" >> /etc/group \
  && echo "python:x:1001:" >> /etc/group \
  && echo "python:x:1000:1001::/home/python:" >> /etc/passwd \
  && python --version \
  && ln -s /usr/local/bin/python /usr/local/bin/python3

# Now copy the app, install dependencies, and ensure python user can access all app files
WORKDIR /app

COPY --chown=python:python ./requirements.txt requirements.txt
COPY --chown=python:python ./pyproject.toml pyproject.toml
RUN python -m pip install --upgrade pip \
  && python -m pip install --no-cache-dir --upgrade -r requirements.txt \
  && python -m pip install -e . \
  && chown python:python -R /app
COPY --chown=python:python . .

# Now we can remove unwanted binaries
RUN rm /bin/echo /bin/ln /bin/rm /bin/sh /bin/chown

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
