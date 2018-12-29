
import dropbox
import json

configuration_file = "configuration.json"


def load_configuration():
    with open(configuration_file, 'r') as f:
        return json.load(f)


def get_direct_download_link(dbx, path):
    shared_link_metadata = dbx.sharing_create_shared_link(path)
    # replacing dl=0 to dl=1, changes it from a website, to a direct dowload to a file/zip of a folder
    return shared_link_metadata.url.replace("dl=0", "dl=1")


if __name__ == "__main__":
    dbx = dropbox.Dropbox(load_configuration()["ACCESS_TOKEN"])

    print(get_direct_download_link(dbx, "/Eppe's Stuff/ApiTest/AFolder"))
