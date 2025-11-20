# hash:sha256:9689a0b84cd4878978ac83acd5f4e4775d1f34c4cb181f26154a0f1d77e16b0d
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:24.5.0-0-python3.12.4-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_ASKPASS
COPY git-askpass /

RUN --mount=type=secret,id=git-access-token \
    GIT_ACCESS_TOKEN="$(cat /run/secrets/git-access-token)" \
    pip install -U --no-cache-dir \
    aind-nwb-utils==0.1.2 \
    pandas==2.3.3 \
    pydantic-settings==2.11.0 \
    -e git+https://github.com/rly/ndx-events@909f09a962c69bfd0cb1f92599f95f5931b56a79#egg=ndx-events
