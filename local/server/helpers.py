import traceback

from . import lookup


def validate_server(server: str) -> str:
    print(server)
    try:
        server_data = lookup.get_server(server)
    except Exception as e:
        traceback.print_exception(e)
        raise e

    print(server_data)
    print(server_data.id)
    return server_data.id
