FROM python:3.10

# Switching to root to install the required packages
USER root

# Update OS and install packages
RUN apt-get update --yes && \
    apt-get dist-upgrade --yes && \
    apt-get install --yes \
      build-essential \
      curl \
      git \
      cmake \
      wget \
      gcc \
      ninja-build \
      libboost-all-dev \
      vim \
      libsqlite3-dev \
      libssl-dev \
      libffi-dev \
      libsasl2-dev \
      default-libmysqlclient-dev \
      netcat \
      iputils-ping && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create an application user
RUN useradd app_user --create-home

ARG APP_DIR=/app

RUN mkdir --parents ${APP_DIR} && \
    chown app_user:app_user ${APP_DIR} && \
    chown --recursive app_user:app_user /usr/local

USER app_user

WORKDIR ${APP_DIR}

# Setup a Virtual environment
ENV VIRTUAL_ENV=${APP_DIR}/venv
RUN python3 -m venv ${VIRTUAL_ENV} && \
    echo ". ${VIRTUAL_ENV}/bin/activate" >> ~/.bashrc && \
    . ~/.bashrc && \
    pip install --upgrade setuptools pip

# Set the PATH so that the Python Virtual environment is referenced for subsequent RUN steps (hat tip: https://pythonspeed.com/articles/activate-virtualenv-dockerfile/)
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Copy the application code into the image
COPY --chown=app_user:app_user . ./adbc

WORKDIR ${APP_DIR}/adbc

# Install Apache Superset
RUN pip install ./apache-superset

# Build Arrow/PyArrow
RUN scripts/build_arrow.sh

# Install ADBC Driver Manager
RUN pip install adbc_driver_manager --index-url https://repo.fury.io/arrow-adbc-nightlies/ --extra-index-url https://pypi.org/simple/

# Install the local ADBC SQLAlchemy driver project
RUN pip install .
