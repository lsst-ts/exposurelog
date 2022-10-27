#!/bin/bash

# This script updates packages in the base Docker image that's used by both the
# build and runtime images, and gives us a place to install additional
# system-level packages with apt-get.
#
# Based on the blog post:
# https://pythonspeed.com/articles/system-packages-docker/

# Bash "strict mode", to help catch problems and bugs in the shell
# script. Every bash script you write should include this. See
# http://redsymbol.net/articles/unofficial-bash-strict-mode/ for
# details.
set -euo pipefail

# Display each command as it's run.
set -x

# Tell apt-get we're never going to be able to give manual
# feedback:
export DEBIAN_FRONTEND=noninteractive

# Update the package listing, so we know what packages exist:
apt-get update

# Install security updates:
apt-get -y upgrade

# Install git so we can upload the Docker image;
# --no-install-recommends prevents installing unnecessary extras;
apt-get -y install --no-install-recommends git

# Install a modern C++ compiler, to build daf_butler dependencies;
# Remove this when we switch to a web-based butler service:
apt-get -y install --no-install-recommends build-essential

# Install libpq-dev for Butlers that use postgres
apt-get -y install --no-install-recommends libpq-dev

# Delete cached files we don't need anymore:
apt-get clean
rm -rf /var/lib/apt/lists/*
