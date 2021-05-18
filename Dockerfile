# This Dockerfile has four stages:
#
# base-image
#   Updates the base Python image with security patches and common system
#   packages. This image becomes the base of all other images.
# dependencies-image
#   Installs third-party dependencies (requirements/main.txt) into a virtual
#   environment. This virtual environment is ideal for copying across build
#   stages.
# install-image
#   Installs the app into the virtual environment.
# runtime-image
#   - Copies the virtual environment into place.
#   - Runs a non-root user.
#   - Configures gunicorn.

FROM tiangolo/uvicorn-gunicorn:python3.8-slim AS base-image

# Update system packages
COPY scripts/install-base-packages.sh .
RUN ./install-base-packages.sh
RUN rm ./install-base-packages.sh

FROM base-image AS dependencies-image

# Put the latest pip and setuptools in the virtualenv
RUN pip install --upgrade --no-cache-dir pip setuptools wheel

# Install the app's Python runtime dependencies
COPY requirements/main.txt ./requirements.txt
RUN pip install --quiet --no-cache-dir -r requirements.txt

FROM dependencies-image AS runtime-image

# Install the web application
COPY . /app
RUN pip install --no-cache-dir /app

# Create a non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Switch to non-root user
USER appuser

# Copy the test butler registry to allow us to run the application with it
COPY tests/data/hsc_raw hsc_raw

# We use a module name other than app, so tell the base image that.  This
# does not copy the app into /app as is recommended by the base Docker
# image documentation and instead relies on the module search path as
# modified by the virtualenv.
ENV MODULE_NAME=exposurelog.main

# The default starts 40 workers, which exhausts the available connections
# on a micro Cloud SQL PostgreSQL server and seems excessive since we can
# scale with Kubernetes.  Cap the workers at 10.
ENV MAX_WORKERS=10

# Our Kubernetes does not allow serving on the default port 80.
ENV PORT=8080
EXPOSE 8080
