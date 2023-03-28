import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

import re
import adbc_driver_flightsql.dbapi as flight_sql
from sqlalchemy import pool
from sqlalchemy import types as sqltypes
from sqlalchemy import util
from sqlalchemy.dialects.postgresql.base import PGInspector
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine.url import URL

from .datatypes import register_extension_types

__version__ = "0.0.1"

if TYPE_CHECKING:
    from sqlalchemy.base import Connection
    from sqlalchemy.engine.interfaces import _IndexDict

register_extension_types()


class DBAPI:
    paramstyle = flight_sql.paramstyle
    apilevel = flight_sql.apilevel
    threadsafety = flight_sql.threadsafety

    # this is being fixed upstream to add a proper exception hierarchy
    Error = getattr(flight_sql, "Error", RuntimeError)
    TransactionException = getattr(flight_sql, "TransactionException", Error)
    ParserException = getattr(flight_sql, "ParserException", Error)

    @staticmethod
    def Binary(x: Any) -> Any:
        return x


class FlightSQLInspector(PGInspector):
    def get_check_constraints(
            self, table_name: str, schema: Optional[str] = None, **kw: Any
    ) -> List[Dict[str, Any]]:
        try:
            return super().get_check_constraints(table_name, schema, **kw)
        except Exception as e:
            raise NotImplementedError() from e


class ConnectionWrapper:
    __c: "Connection"
    notices: List[str]
    autocommit = None  # duckdb doesn't support setting autocommit
    closed = False

    def __init__(self, c: flight_sql.Connection) -> None:
        self.__c = c
        self.notices = list()

    def cursor(self) -> flight_sql.Cursor:
        return self.__c.cursor()

    def fetchmany(self, size: Optional[int] = None) -> List:
        return self.__c.fetchmany(size)

    @property
    def c(self) -> "Connection":
        warnings.warn(
            "Directly accessing the internal connection object is deprecated (please go via the __getattr__ impl)",
            DeprecationWarning,
        )
        return self.__c

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__c, name)

    @property
    def connection(self) -> "Connection":
        return self

    def close(self) -> None:
        self.__c.close()

    @property
    def rowcount(self) -> int:
        return self.cursor().rowcount

    def executemany(
            self,
            statement: str,
            parameters: Optional[List[Dict]] = None,
            context: Optional[Any] = None,
    ) -> None:
        self.cursor().executemany(statement, parameters)

    def execute(
            self,
            statement: str,
            parameters: Optional[Tuple] = None,
            context: Optional[Any] = None,
    ) -> None:
        try:
            if statement.lower() == "commit":  # this is largely for ipython-sql
                self.__c.commit()
            elif statement.lower() == "register":
                assert parameters and len(parameters) == 2, parameters
                view_name, df = parameters
                self.__c.register(view_name, df)
            else:
                with self.__c.cursor() as cur:
                    cur.execute(statement, parameters)
        except RuntimeError as e:
            if e.args[0].startswith("Not implemented Error"):
                raise NotImplementedError(*e.args) from e
            elif (
                    e.args[0]
                    == "TransactionContext Error: cannot commit - no transaction is active"
            ):
                return
            else:
                raise e


class DuckDBEngineWarning(Warning):
    pass


class Dialect(PGDialect_psycopg2):
    name = "adbc_flight_sql"
    driver = "adbc_flight_sql_driver"
    _has_events = False
    supports_statement_cache = False
    supports_comments = False
    supports_sane_rowcount = False
    supports_server_side_cursors = False
    inspector = PGInspector
    # colspecs TODO: remap types to duckdb types
    colspecs = util.update_copy(
        PGDialect_psycopg2.colspecs,
        {
            # the psycopg2 driver registers a _PGNumeric with custom logic for
            # postgres type_codes (such as 701 for float) that duckdb doesn't have
            sqltypes.Numeric: sqltypes.Numeric,
            sqltypes.Interval: sqltypes.Interval,
        },
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["use_native_hstore"] = False
        super().__init__(*args, **kwargs)

    def connect(self, *cargs: Any, **cparams: Any) -> "Connection":
        protocol: str = "grpc"
        use_encryption: bool = cparams.get("useEncryption", "False").lower() == "true"
        if use_encryption:
            protocol += "+tls"

        disable_certificate_verification: bool = cparams.get("disableCertificateVerification", "False").lower() == "true"

        uri = f"{protocol}://{cparams.get('host')}:{cparams.get('port')}"
        user = cparams.get('user')
        password = cparams.get('password')

        conn = flight_sql.connect(uri=uri,
                                  db_kwargs={"username": user,
                                             "password": password,
                                             "adbc.flight.sql.client_option.tls_skip_verify": str(disable_certificate_verification).lower()
                                             }
                                  )

        # Add a notices attribute for the PostgreSQL / DuckDB dialect...
        setattr(conn, "notices", ["n/a"])

        return ConnectionWrapper(conn)

    def on_connect(self) -> None:
        pass

    @classmethod
    def get_pool_class(cls, url: URL) -> Type[pool.Pool]:
        return pool.QueuePool

    @staticmethod
    def dbapi(**kwargs: Any) -> Type[DBAPI]:
        return DBAPI

    def _get_server_version_info(self, connection: "Connection") -> Tuple[int, int]:
        return (8, 0)

    def get_default_isolation_level(self, connection: "Connection") -> None:
        raise NotImplementedError()

    def do_rollback(self, connection: "Connection") -> None:
        with connection.cursor() as cur:
            cur.execute("rollback")

    def do_begin(self, connection: "Connection") -> None:
        with connection.cursor() as cur:
            cur.execute("begin")

    def do_commit(self, connection: "Connection") -> None:
        with connection.cursor() as cur:
            cur.execute("commit")

    def get_schema_names(
            self,
            connection: Any,
            **kw: Any,
    ) -> Any:
        s = "SELECT schema_name FROM information_schema.schemata WHERE catalog_name=current_database() ORDER BY 1 ASC"
        with connection.connection.cursor() as cur:
            cur.execute(operation=s)
            rs = cur.fetchall()

        return [row[0] for row in rs]

    def get_table_names(
            self,
            connection: Any,
            schema: Optional[Any] = None,
            include: Optional[Any] = None,
            **kw: Any,
    ) -> Any:
        s = "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema=? ORDER BY 1 ASC"
        with connection.connection.cursor() as cur:
            cur.execute(operation=s, parameters=[schema if schema is not None else "main"])
            rs = cur.fetchall()

        return [row[0] for row in rs]

    def get_view_names(
            self,
            connection: Any,
            schema: Optional[Any] = None,
            include: Optional[Any] = None,
            **kw: Any,
    ) -> Any:
        s = "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW' AND table_schema=? ORDER BY 1"
        with connection.connection.cursor() as cur:
            cur.execute(operation=s, parameters=[schema if schema is not None else "main"])
            rs = cur.fetchall()

        return [row[0] for row in rs]

    def get_check_constraints(self, connection, table_name, schema=None, **kw):
        table_oid = self.get_table_oid(
            connection, table_name, schema, info_cache=kw.get("info_cache")
        )

        CHECK_SQL = """
            SELECT
                cons.conname as name,
                pg_get_constraintdef(cons.oid, true) as src
            FROM
                pg_catalog.pg_constraint cons
            WHERE
                cons.conrelid = ? AND
                cons.contype = 'c'
        """

        with connection.connection.cursor() as cur:
            cur.execute(operation=CHECK_SQL, parameters=[table_oid])
            rs = cur.fetchall()

        ret = []
        for name, src in rs:
            # samples:
            # "CHECK (((a > 1) AND (a < 5)))"
            # "CHECK (((a = 1) OR ((a > 2) AND (a < 5))))"
            # "CHECK (((a > 1) AND (a < 5))) NOT VALID"
            # "CHECK (some_boolean_function(a))"
            # "CHECK (((a\n < 1)\n OR\n (a\n >= 5))\n)"

            m = re.match(
                r"^CHECK *\((.+)\)( NOT VALID)?$", src, flags=re.DOTALL
            )
            if not m:
                util.warn("Could not parse CHECK constraint text: %r" % src)
                sqltext = ""
            else:
                sqltext = re.compile(
                    r"^[\s\n]*\((.+)\)[\s\n]*$", flags=re.DOTALL
                ).sub(r"\1", m.group(1))
            entry = {"name": name, "sqltext": sqltext}
            if m and m.group(2):
                entry["dialect_options"] = {"not_valid": True}

            ret.append(entry)
        return ret

    def get_indexes(
            self,
            connection: "Connection",
            table_name: str,
            schema: Optional[str] = None,
            **kw: Any,
    ) -> List["_IndexDict"]:
        warnings.warn(
            "duckdb-engine doesn't yet support reflection on indices",
            DuckDBEngineWarning,
        )
        return []
