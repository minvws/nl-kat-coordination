import requests

KATALOGUS_API = "http://localhost:8003"


def run():
    # Create organisations
    for n in range(1, 10):
        requests.post(
            url=f"{KATALOGUS_API}/v1/organisations",
            data={
                "id": f"org-{n}",
                "name": f"Organisation {n}",
            },
        )


if __name__ == "__main__":
    run()
