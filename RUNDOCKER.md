# Superset server with the SQLAlchemy ADBC->Flight SQL dialect (driver)

## Running from the published Docker image

Open a terminal, then pull and run the published Docker image which has everything setup (change: "--detach" to "--interactive" if you wish to see the stdout on your screen) - with command:

```bash
docker run --name superset-sqlalchemy-adbc-flight-sql \
           --interactive \
           --rm \
           --tty \
           --init \
           --publish 8088:8088 \
           --env SUPERSET_ADMIN_PASSWORD="admin" \
           --pull missing \
           --entrypoint /bin/bash \
           prmoorevoltron/superset-sqlalchemy-adbc-flight-sql:latest
````
