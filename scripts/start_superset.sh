#!/usr/bin/env bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
set -e

source ~/.bashrc

echo_step() {
cat <<EOF

######################################################################


Init Step ${1} [${2}] -- ${3}


######################################################################

EOF
}

SUPERSET_INIT_COMPLETE_FILE="~/.superset/superset_init_complete.txt"

# Determine if we should apply the Superset init steps
if [ ! -f ${SUPERSET_INIT_COMPLETE_FILE} ]
then
  SUPERSET_INIT=1
  echo "NOTE: We will run the Superset init steps b/c the ${SUPERSET_INIT_COMPLETE_FILE} file does not exist"
else
  SUPERSET_INIT=0
  echo "NOTE: We will skip Superset init steps b/c the ${SUPERSET_INIT_COMPLETE_FILE} file exists"
fi

# Create a superset config file with a secure SECRET_KEY if it isn't present
if [ ! -f superset_config.py ]
then
  echo "Creating superset_config.py file b/c it is not present..."
  echo "SECRET_KEY='$(openssl rand -base64 42)'" > superset_config.py
fi

# Start superset
echo_step "1" "Starting" "Start Superset"

HYPHEN_SYMBOL='-'

gunicorn \
    --bind "${SUPERSET_BIND_ADDRESS:-0.0.0.0}:${SUPERSET_PORT:-8088}" \
    --access-logfile "${ACCESS_LOG_FILE:-$HYPHEN_SYMBOL}" \
    --error-logfile "${ERROR_LOG_FILE:-$HYPHEN_SYMBOL}" \
    --workers ${SERVER_WORKER_AMOUNT:-1} \
    --worker-class ${SERVER_WORKER_CLASS:-gthread} \
    --threads ${SERVER_THREADS_AMOUNT:-20} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --keep-alive ${GUNICORN_KEEPALIVE:-2} \
    --max-requests ${WORKER_MAX_REQUESTS:-0} \
    --max-requests-jitter ${WORKER_MAX_REQUESTS_JITTER:-0} \
    --limit-request-line ${SERVER_LIMIT_REQUEST_LINE:-0} \
    --limit-request-field_size ${SERVER_LIMIT_REQUEST_FIELD_SIZE:-0} \
    "${FLASK_APP}" &

sleep 10
echo_step "1" "Complete" "Start Superset"

if [ "${SUPERSET_INIT}" == 1 ]
then
  # Initialize the database
  echo_step "2" "Starting" "Applying DB migrations"
  superset db upgrade
  echo_step "2" "Complete" "Applying DB migrations"

  # Create an admin user
  echo_step "3" "Starting" "Setting up admin user ( admin )"
  superset fab create-admin \
                --username admin \
                --firstname Superset \
                --lastname Admin \
                --email admin@superset.com \
                --password "${SUPERSET_ADMIN_PASSWORD:-admin}"
  echo_step "3" "Complete" "Setting up admin user"

  # Create default roles and permissions
  echo_step "4" "Starting" "Setting up roles and perms"
  superset init
  echo_step "4" "Complete" "Setting up roles and perms"

  # Create the SUPERSET_INIT_COMPLETE_FILE file so container restarts do not run all of the init steps...
  mkdir -p $(dirname ${SUPERSET_INIT_COMPLETE_FILE})
  touch ${SUPERSET_INIT_COMPLETE_FILE}

fi

# Wait forever on superset server background process
wait
