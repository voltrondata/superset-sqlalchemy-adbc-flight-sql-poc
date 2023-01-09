from sqlalchemy.engine import URL
from sqlalchemy import create_engine

database_url = URL.create(
    drivername="adbc_flight_sql",
    username="flight_username",
    password="flight_password",
    host="localhost",
    port=31337,
    query=dict(useEncryption="True",
               disableCertificateVerification="True"
               )
)

print(f"database_url={database_url}")
e = create_engine(url=database_url)

with e.connect() as conn:
    with conn.begin():
        conn.execute("insert into nation (n_nationkey, n_name, n_regionkey, n_comment) values (?, ?, ?, ?)",
                     (9999, 'TEST_NATION', 1, 'TESTING 123')
                     )
        print(conn.execute(statement="SELECT * FROM nation WHERE n_nationkey = 9999").fetchall())


print("All done")
