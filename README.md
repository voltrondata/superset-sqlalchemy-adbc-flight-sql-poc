# Apache Superset using the new Python ADBC driver for Flight SQL 

This repo demonstrates the use of the new Python ADBC Flight SQL driver with SQLAlchemy and Apache Superset as a front-end.

Note: this repo contains pre-release nightly Apache Arrow Flight SQL drivers which are subject to change.  It also uses a git sub-module pointing to Apache Superset as it was on 07-Feb-2023.

The SQLAlchemy ADBC Flight SQL driver used here is designed for a Flight SQL server running a PostgreSQL-type dialect (such as PostgreSQL or DuckDB) - meaning it has the Postgres-style information schema tables available.

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
git clone https://github.com/voltrondata/superset-sqlalchemy-adbc-flight-sql-poc --recurse-submodules

cd superset-sqlalchemy-adbc-flight-sql-poc
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

a. Click "Settings" in the upper-right, then under "Data" - click: "Database Connections"   
![Database Connections screenshot](images/superset_database_connections_screenshot.png?raw=true "Database Connections")

b. On the next screen - click: "+ DATABASE" - also in the upper-right, just under: "Settings"   
![Create Database screenshot](images/superset_database_button_screenshot.png?raw=true "Create Database")

c. When the "Connect a Database" window opens up - click the "SUPPORTED DATABASES" drop-down and choose: "Other"

d. Type "Flight SQL" for "DISPLAY NAME"

e. Enter the SQLALCHEMY URI value of:

```
adbc_flight_sql://flight_username:flight_password@host.docker.internal:31337?disableCertificateVerification=True&useEncryption=True
```

f. Click the "TEST CONNECTION" button - you should see a message on the lower-right say: "Connection looks good!" - your window should look like this:   
![Connection looks good screenshot](images/superset_connection_looks_good_screenshot.png?raw=true "Connection looks good")

g. Click the blue "CONNECT" on the lower-right to save the Database connection

### 2. Use the new "Flight SQL" connection you just created in the SQL Lab

a. Click "SQL" in the Superset main menu (top-left of screen), then choose: "SQL Lab"   
![SQL Lab menu option screenshot](images/superset_sql_lab_menu_option_screnshot.png?raw=true "SQL Lab menu option")

b. Type a query in the SQL window on the right - something like:   
```SELECT * FROM customer;```

c. Click the blue: "RUN SELECTION" button.  You should see data appear below the query.  Your window should look like this:   
![SQL Lab query results screenshot](images/superset_sql_lab_query_results_screenshot.png?raw=true "SQL Lab query results")

## Tear Down
Just stop the docker containers with these commands:

```bash
docker kill superset-sqlalchemy-adbc-flight-sql
docker kill flight-sql
```
