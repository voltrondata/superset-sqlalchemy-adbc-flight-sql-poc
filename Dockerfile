FROM python:3.12.0rc1

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

# Install Apache Superset (using source)
RUN cp ./superset_config_files/setup.py ./apache-superset && \
    cp ./superset_config_files/sql_lab.py ./apache-superset/superset/sql_lab.py && \
    pip install --editable ./apache-superset

# Install Poetry package manager and then install the local ADBC SQLAlchemy driver project
ENV POETRY_VIRTUALENVS_CREATE="false"
RUN pip install poetry && \
    poetry install

ENV FLASK_APP="superset.app:create_app()"

# Build javascript assets
WORKDIR ${APP_DIR}/adbc/apache-superset/superset-frontend
RUN npm ci && \
    npm run build

# Initialize superset
WORKDIR ${APP_DIR}/adbc

EXPOSE 8088

ENTRYPOINT ["scripts/start_superset.sh"]
