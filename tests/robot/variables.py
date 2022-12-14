xtdb_itest_vars = {
    "OCTOPOES_URI": "http://localhost:29000/_dev",
    "XTDB_URI": "http://localhost:29002/_xtdb",
    "QUEUE_URI": "amqp://ci_user:ci_pass@localhost:29004/kat",
    "RABBIT_MQ_API_URI": "http://ci_user:ci_pass@localhost:29003/api",
}

crux_itest_vars = {
    "OCTOPOES_URI": "http://localhost:28000/_dev",
    "XTDB_URI": "http://localhost:28002/_crux",
    "QUEUE_URI": "amqp://ci_user:ci_pass@localhost:28004/kat",
    "RABBIT_MQ_API_URI": "http://ci_user:ci_pass@localhost:28003/api",
}


def get_variables(env: str) -> dict:
    if env == "xtdb":
        return xtdb_itest_vars
    elif env == "crux":
        return crux_itest_vars
    return {}
