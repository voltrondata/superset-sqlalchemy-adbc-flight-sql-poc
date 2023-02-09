import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

#import duckdb
import base64
from pyarrow import flight_sql
from adbc_driver_manager.dbapi import Connection as ADBCFlightSQLConnection, Cursor
from sqlalchemy import pool
from sqlalchemy import types as sqltypes
from sqlalchemy import util
from sqlalchemy.dialects.postgresql.base import PGInspector
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine.url import URL

from .datatypes import register_extension_types

__version__ = "0.6.6"

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
    __c: ADBCFlightSQLConnection
    notices: List[str]
    autocommit = None  # duckdb doesn't support setting autocommit
    closed = False

    def __init__(self, c: ADBCFlightSQLConnection) -> None:
        self.__c = c
        self.notices = list()

    def cursor(self) -> Cursor:
        return self.__c.cursor()

    def fetchmany(self, size: Optional[int] = None) -> List:
        return self.__c.fetchmany(size)

    @property
    def c(self) -> ADBCFlightSQLConnection:
        warnings.warn(
            "Directly accessing the internal connection object is deprecated (please go via the __getattr__ impl)",
            DeprecationWarning,
        )
        return self.__c

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__c, name)

    @property
    def connection(self) -> ADBCFlightSQLConnection:
        return self

    def close(self) -> None:
        ADBCFlightSQLConnection.close()

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

    def connect(self, *cargs: Any, **cparams: Any) -> ADBCFlightSQLConnection:
        uri = f"{cparams.get('protocol')}://{cparams.get('host')}:{cparams.get('port')}"
        user = cparams.get('user')
        password = cparams.get('password')
        authorization_header = f"Basic {str(base64.b64encode(bytes(f'{user}:{password}', encoding='utf-8')), encoding='utf-8')}"

        conn = flight_sql.connect(uri=uri,
                                  db_kwargs={"arrow.flight.sql.authorization_header": authorization_header,
                                             "arrow.flight.sql.client_option.disable_server_verification": "true"
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
        try:
            super().do_rollback(connection)
        except DBAPI.TransactionException as e:
            if (
                e.args[0]
                != "TransactionContext Error: cannot rollback - no transaction is active"
            ):
                raise e

    def do_begin(self, connection: "Connection") -> None:
        with connection.cursor() as cur:
            cur.execute("begin")

    def get_view_names(
        self,
        connection: Any,
        schema: Optional[Any] = None,
        include: Optional[Any] = None,
        **kw: Any,
    ) -> Any:
        s = "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW' and table_schema=?"
        with connection.cursor() as cur:
            rs = cur.execute(s, schema if schema is not None else "main")

        return [row[0] for row in rs]

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
