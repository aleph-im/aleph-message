import json
from os import makedirs
from os.path import abspath, join

import requests

ALEPH_API_SERVER = "https://api2.aleph.im"
MESSAGES_STORAGE_PATH: str = abspath(join(__file__, "../test_messages"))


def download_messages(pages: int, quiet: bool = False):
    assert pages >= 1
    path = "/api/v0/messages.json"

    for page in range(1, pages):
        if not quiet:
            print(f"Downloading page {page:03}/{pages:03} ...")
        response = requests.get(f"{ALEPH_API_SERVER}{path}?page={page}")
        response.raise_for_status()
        data_dict = response.json()
        makedirs(MESSAGES_STORAGE_PATH, exist_ok=True)
        with open(join(MESSAGES_STORAGE_PATH, f"{page}.json"), "w") as page_fd:
            json.dump(data_dict, page_fd)

    if not quiet:
        print("Finished")


if __name__ == "__main__":
    download_messages(pages=10000)
