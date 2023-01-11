from sqlalchemy.engine import URL
from sqlalchemy import create_engine
import sqlalchemy

database_url = URL.create(
    drivername="adbc_flight_sql",
    username="flight_username",
    password="flight_password",
    host="localhost",  # If running in a Docker container - use value: "host.docker.internal"
    port=31337,
    query=dict(useEncryption="True",
               disableCertificateVerification="True"
               )
)

# Example url (for Docker)
# adbc_flight_sql://flight_username:flight_password@host.docker.internal:31337?disableCertificateVerification=True&useEncryption=True

print(f"database_url={database_url}")
e = create_engine(url=database_url)

with e.connect() as conn:
    with conn.begin():
        print(conn.execute(statement="SELECT * FROM nation WHERE n_nationkey = 9999").fetchall())


print("All done")
