def remove_trailing_slash(url: str) -> str:
    """Remove trailing slash from url."""
    if url.endswith("/"):
        return url[:-1]
    return url
