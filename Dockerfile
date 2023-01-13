FROM python:3.10

# Switching to root to install the required packages
USER root

# Update OS and install packages
RUN apt-get update --yes && \
    apt-get dist-upgrade --yes && \
    apt-get install --yes \
        build-essential \
        ca-certificates \
        chromium \
        cmake \
        curl \
        default-libmysqlclient-dev \
        gcc \
        git \
        iputils-ping \
        libboost-all-dev \
        libffi-dev \
        libldap2-dev \
        libsasl2-dev \
        libsqlite3-dev \
        libssl-dev \
        netcat \
        ninja-build \
        sqlite3 \
        vim \
        wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install NodeJS (needed for Apache Superset)
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get install -y nodejs

# Create an application user
RUN useradd app_user --create-home

ARG APP_DIR=/app

RUN mkdir --parents ${APP_DIR} && \
    chown app_user:app_user ${APP_DIR} && \
    chown --recursive app_user:app_user /usr/local

USER app_user

WORKDIR ${APP_DIR}

# Setup a Python Virtual environment
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

# Build Arrow/PyArrow
RUN scripts/build_arrow.sh

# Install ADBC Driver Manager
RUN pip install adbc_driver_manager --index-url https://repo.fury.io/arrow-adbc-nightlies/ --extra-index-url https://pypi.org/simple/

# Install the local ADBC SQLAlchemy driver project
RUN pip install .

# Install numpy version 1.23.5 as required by superset
RUN pip install numpy==1.23.5

# Install Apache Superset
RUN pip install --editable ./apache-superset

ENV FLASK_APP="superset"

WORKDIR ${APP_DIR}/adbc/apache-superset/superset-frontend
RUN npm install -f --no-optional webpack webpack-cli && \
    npm install -f --no-optional && \
    echo "Building frontend" && \
    npm run build-dev

# Initialize superset
WORKDIR ${APP_DIR}/adbc

EXPOSE 8088
