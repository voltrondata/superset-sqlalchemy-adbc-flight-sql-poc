# Apache Superset using the new Python ADBC driver for Flight SQL 

This repo demonstrates the use of the new Python ADBC Flight SQL driver with SQLAlchemy and Apache Superset as a front-end.

Note: this repo contains pre-release nightly Apache Arrow Flight SQL drivers which are subject to change.  It also uses a git sub-module pointing to Apache Superset as it was on 07-Feb-2023. 

## Option 1 - Running the published Docker image
The easiest way to run this solution is to use the published Docker image - along with a running Flight SQL Server container.

### Step 1 - Run an Arrow Flight SQL Docker container (see repo: https://github.com/voltrondata/flight-sql-server-example for more details)
```bash
docker run --name flight-sql \
           --detach \
           --rm \
           --tty \
           --init \
           --publish 31337:31337 \
           --env FLIGHT_PASSWORD="flight_password" \
           --pull missing \
           voltrondata/flight-sql:latest

```

### Step 2 - Run the published Superset image which has the ADBC driver setup already:
```bash
docker run --name superset-sqlalchemy-adbc-flight-sql \
           --detach \
           --rm \
           --tty \
           --init \
           --publish 8088:8088 \
           --env SUPERSET_ADMIN_PASSWORD="admin" \
           --pull missing \
           prmoorevoltron/superset-sqlalchemy-adbc-flight-sql:latest
```

### Step 3 - Wait about 1 minute for the Superset server to initialize - then open a browser and go to:   
http://localhost:8088   

Connect with username: "admin" and password: "admin" (or whatever you set env var: "SUPERSET_ADMIN_PASSWORD" to in the command above)

## Option 2 - Building a Docker container from this repo on your computer

### Step 1 - Clone this repo:
```bash
git clone https://github.com/voltrondata/superset-sqlalchemy-adbc-flight-sql-poc

cd superset-sqlalchemy-adbc-flight-sql-poc

# Update sub-modules (pulls the Superset source code)
git submodule update --init
```

### Step 2 - Build the Docker container
```bash
docker build . --tag=local-superset
```

### Step 3 - Run an Arrow Flight SQL Docker container (see repo: https://github.com/voltrondata/flight-sql-server-example for more details)
```bash
docker run --name flight-sql \
           --detach \
           --rm \
           --tty \
           --init \
           --publish 31337:31337 \
           --env FLIGHT_PASSWORD="flight_password" \
           --pull missing \
           voltrondata/flight-sql:latest

```

### Step 2 - Run the Superset docker image you just built:
```bash
docker run --name superset-sqlalchemy-adbc-flight-sql \
           --detach \
           --rm \
           --tty \
           --init \
           --publish 8088:8088 \
           --env SUPERSET_ADMIN_PASSWORD="admin" \
           --pull missing \
           local-superset
```

## Browser steps once you have Superset up and running

### 1. Create a Database connection

#### a. Click "Settings" in the upper-right, then under "Data" - click: "Database Connections"

#### b. On the next screen - click: "+ DATABASE" - also in the upper-right, just under: "Settings"

#### c. When the "Connect a Database" window opens up - click the "SUPPORTED DATABASES" drop-down and choose: "Other"

#### d. Type "Flight SQL" for "DISPLAY NAME"

#### e. Enter the SQLALCHEMY URI value of:
```
adbc_flight_sql://flight_username:flight_password@host.docker.internal:31337?disableCertificateVerification=True&useEncryption=True
```

#### f. Click the "TEST CONNECTION" button - you should see a message on the lower-right say: "Connection looks good!"

#### g. Click "CONNECT" to save the Database connection

### 2. Use the new "Flight SQL" connection you just created in the SQL Lab

#### a. Click "SQL" in the Superset main menu (top-left of screen), then choose: "SQL Lab"

#### b. Type a query in the SQL window on the right - something like:
```SELECT * FROM customer```

#### c. Click the blue: "RUN SELECTION" button.  You should see data appear below the query.
