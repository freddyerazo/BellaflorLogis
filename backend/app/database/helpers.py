from uuid import UUID


def build_set_clause(data: dict) -> str:
    return ", ".join(f"{key} = :{key}" for key in data)


def jsonable_params(data: dict) -> dict:
    return {
        key: (str(value) if isinstance(value, UUID) else value)
        for key, value in data.items()
    }
