import requests
import os
import json
from http import HTTPStatus


PORT: int = 8088


def main():
    # Authenticate
    token_response = requests.post(url=f'http://localhost:{PORT}/api/v1/security/login',
                                   data=json.dumps(dict(password=os.getenv("SUPERSET_ADMIN_PASSWORD", "admin"),
                                                        provider="db",
                                                        refresh=True,
                                                        username=os.getenv("SUPERSET_ADMIN_USERNAME", "admin")
                                                        )
                                                   ),
                                   headers={'Content-Type': 'application/json',
                                            'Accept': 'application/json'
                                            }
                                   )
    if token_response.status_code != HTTPStatus.OK:
        raise Exception("Invalid credentials!")

    # # Attempt to create the Flight SQL Database connection
    # {
    #     "allow_ctas": true,
    #     "allow_cvas": true,
    #     "allow_dml": true,
    #     "allow_file_upload": true,
    #     "allow_run_async": true,
    #     "cache_timeout": 0,
    #     "configuration_method": "sqlalchemy_form",
    #     "database_name": "string",
    #     "driver": "string",
    #     "engine": "string",
    #     "expose_in_sqllab": true,
    #     "external_url": "string",
    #     "extra": "string",
    #     "force_ctas_schema": "string",
    #     "impersonate_user": true,
    #     "is_managed_externally": true,
    #     "masked_encrypted_extra": "string",
    #     "parameters": {
    #         "additionalProp1": "string",
    #         "additionalProp2": "string",
    #         "additionalProp3": "string"
    #     },
    #     "server_cert": "string",
    #     "sqlalchemy_uri": "string",
    #     "ssh_tunnel": {
    #         "password": "string",
    #         "private_key": "string",
    #         "private_key_password": "string",
    #         "server_address": "string",
    #         "server_port": 0,
    #         "username": "string"
    #     },
    #     "uuid": "string"
    # }
    #
    # {
    #     "allow_ctas": false,
    #     "allow_cvas": false,
    #     "allow_dml": false,
    #     "allow_file_upload": false,
    #     "allow_run_async": false,
    #     "allows_cost_estimate": false,
    #     "allows_subquery": true,
    #     "allows_virtual_table_explore": true,
    #     "backend": "adbc_flight_sql",
    #     "changed_on": "2023-01-12T18:58:29.471579",
    #     "changed_on_delta_humanized": "21 hours ago",
    #     "created_by": {
    #         "first_name": "admin",
    #         "last_name": "user"
    #     },
    #     "database_name": "Flight SQL",
    #     "disable_data_preview": false,
    #     "engine_information": {
    #         "supports_file_upload": true
    #     },
    #     "explore_database_id": 1,
    #     "expose_in_sqllab": true,
    #     "extra": "{\"allows_virtual_table_explore\":true}",
    #     "force_ctas_schema": null,
    #     "id": 1,
    #     "uuid": "3857ba36-ff0b-4b66-90d3-1b401bdd02f8"
    # }


if __name__ == '__main__':
    main()