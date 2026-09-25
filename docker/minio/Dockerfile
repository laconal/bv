# MinIO no longer publishes images - Docker Hub and quay.io both refuse
# anonymous pulls since 2026-09 - so the final community releases are built
# from their (archived, AGPLv3) source instead. One image carries both
# binaries: `minio` for the server, `mc` for the minio-init bucket bootstrap
# (see docker-compose.yaml).

FROM golang:1.24-alpine AS build

ARG MINIO_RELEASE=RELEASE.2025-09-07T16-13-09Z
ARG MC_RELEASE=RELEASE.2025-08-13T08-35-41Z

ENV CGO_ENABLED=0

RUN apk add --no-cache git

WORKDIR /src

# gen-ldflags.go stamps the version shown by `minio --version`; it takes the
# release timestamp (RELEASE.2025-09-07T16-13-09Z -> 2025-09-07T16:13:09Z)
# and reads the commit id via git, hence a real clone rather than a tarball.
RUN git clone --depth 1 --branch "$MINIO_RELEASE" https://github.com/minio/minio.git \
    && cd minio \
    && version=$(echo "${MINIO_RELEASE#RELEASE.}" | sed -E 's/T([0-9]+)-([0-9]+)-([0-9]+)Z/T\1:\2:\3Z/') \
    && go build -tags kqueue -trimpath \
        -ldflags "$(MINIO_RELEASE=RELEASE go run buildscripts/gen-ldflags.go "$version")" \
        -o /out/minio

RUN git clone --depth 1 --branch "$MC_RELEASE" https://github.com/minio/mc.git \
    && cd mc \
    && version=$(echo "${MC_RELEASE#RELEASE.}" | sed -E 's/T([0-9]+)-([0-9]+)-([0-9]+)Z/T\1:\2:\3Z/') \
    && go build -tags kqueue -trimpath \
        -ldflags "$(MC_RELEASE=RELEASE go run buildscripts/gen-ldflags.go "$version")" \
        -o /out/mc

FROM alpine:3.24

RUN apk add --no-cache ca-certificates

COPY --from=build /out/minio /out/mc /usr/bin/

EXPOSE 9000 9001

ENTRYPOINT ["minio"]
CMD ["server", "/data"]
