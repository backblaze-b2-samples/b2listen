# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Docker image build for `linux/amd64` and `linux/arm64` on the current `cloudflare/cloudflared` base image (distroless Debian 13)

### Added

- Pull request check that builds the Docker image for both platforms without pushing

## [1.1.0] - 2024-09-03

### Added

- Support for [Backblaze B2 Event Broker](https://github.com/backblaze-b2-samples/b2-event-broker)

## [1.0.1] - 2024-07-31

### Changes

- Clean up Dockerfile to minimize image size
- Clean up source to remove warnings

## [1.0.0] - 2024-07-23

Initial version.
