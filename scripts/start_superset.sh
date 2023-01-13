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

# Determine if we should apply the Superset init steps
if [ ! -f ~/.superset/superset.db ]
then
  SUPERSET_INIT=1
  echo "NOTE: We will run the Superset init steps b/c the superset.db file does not exist"
else
  SUPERSET_INIT=0
  echo "NOTE: We will skip Superset init steps b/c the superset.db file exists"
fi

# Start superset
echo_step "1" "Starting" "Start Superset"
superset run -p 8088 --with-threads --reload --debugger --host 0.0.0.0 &
sleep 10
echo_step "1" "Complete" "Start Superset"

if [ "${SUPERSET_INIT}" == 1 ]
then
  # Initialize the database
  echo_step "2" "Starting" "Applying DB migrations"
  superset db upgrade
  echo_step "2" "Complete" "Applying DB migrations"

  # Create an admin user
  echo_step "3" "Starting" "Setting up admin user ( admin / $ADMIN_PASSWORD )"
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

fi

# Wait forever on superset server background process
wait
