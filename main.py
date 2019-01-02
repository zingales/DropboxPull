
import dropbox
import json
import csv
import pymysql

configuration_file = "configuration.json"


def load_configuration():
    with open(configuration_file, 'r') as f:
        return json.load(f)


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


class RDSInterface(object):

    def __init__(self, rds_host, user, password, db_name):
        self.conn = pymysql.connect(rds_host, user=user,
                                    passwd=password, db=db_name, connect_timeout=5)

    def query_name(self, name_substring):
        cur = self.conn.cursor()
        sql = "select * from raw_dropbox where name like %s"

        cur.execute(sql, ('%' + name_substring + '%'))

        data = cur.fetchall()
        cur.close()

        return data


class DropboxInterface(object):

    def __init__(self, access_token):
        self.dbx = dropbox.Dropbox(access_token)

    def get_direct_download_link(self, path):
        shared_link_metadata = self.dbx.sharing_create_shared_link(
            path, short_url=False)
        # replacing dl=0 to dl=1, changes it from a website, to a direct dowload to a file/zip of a folder
        return shared_link_metadata.url.replace("dl=0", "dl=1")

    def get_folder_metadata(self, path):
        def isFolder(metaData):
            return isinstance(metaData, dropbox.files.FolderMetadata)

        folders = set()
        self.folder_iterator(path, None, isFolder, folders)

        return folders

    def organize_into_folders(self, folders, root_path):
        root_path = root_path.lower()
        organized_folders = dict()

        # we assume folders is sorted
        for folder_path in folders:
            folder_name = remove_prefix(folder_path, root_path + "/")
            path_parts = folder_name.split("/")
            if len(path_parts) == 1:
                organized_folders[path_parts[0]] = folder_path
            else:
                series_name = path_parts[0]
                book_name = path_parts[1]

                if not isinstance(organized_folders[series_name], dict):
                    organized_folders[series_name] = dict()
                organized_folders[series_name][book_name] = folder_path

        return organized_folders

    def generator_book_tuples_from_organized_folders(self, organized_folders):
        for k, v in organized_folders.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    yield gen_book_tuple(name=kk, path=vv, series=k, dropbox_download=self.get_direct_download_link(vv))
            else:
                yield gen_book_tuple(name=k, path=v, series=None, dropbox_download=self.get_direct_download_link(v))

        return None

    def folder_iterator(self, path, cursor, conditional, objects):
        if cursor is None:
            results = self.dbx.files_list_folder(path, recursive=False)
        else:
            results = self.dbx.files_list_folder_continue(cursor)

        for metaData in results.entries:
            if conditional(metaData):
                objects.add(metaData)
                self.folder_iterator(metaData.path_lower, None,
                                     conditional, objects)

        if results.has_more:
            self.folder_iterator(path, results.cursor, conditional, objects)

        return

    def get_book_tuples(self, path):
        tuples = list()
        folders = self.get_folder_metadata(path)
        folder_paths = [folder.path_lower for folder in folders]
        folder_paths.sort()
        organized_folders = self.organize_into_folders(folder_paths, path)
        for val in self.generator_book_tuples_from_organized_folders(organized_folders):
            tuples.append(val)

        return tuples


def write_tuples_to_csv(tuples, csv_path):
    with open(csv_path, 'w') as out:
        csv_out = csv.writer(out)
        csv_out.writerow(['name', 'path', 'series', 'dropbox link'])
        for row in tuples:
            csv_out.writerow(row)


def gen_book_tuple(name, path, series, dropbox_download):
    return (series, name, dropbox_download, path)


def run(dbi):
    # root_folder = load_configuration()["ROOT_FOLDER_PATH"]
    tuples = list()
    for path in load_configuration()["AUDIOBOOK_SOURCES"]:
        tuples.extend(dbi.get_book_tuples(path))

    write_tuples_to_csv(tuples, 'books.csv')


def test1(dbi):
    root_folder = load_configuration()["ROOT_FOLDER_PATH"]
    folder_results = dbi.get_paths_in_order(root_folder)
    for x in folder_results:
        print(x)


def test2(dbi):
    with open('foldersExample.json') as f:
        folders = json.load(f)

    root_folder = load_configuration()["ROOT_FOLDER_PATH"]
    organized_folders = dbi.organize_into_folders(folders, root_folder)
    for val in dbi.generator_book_tuples_from_organized_folders(organized_folders):
        print(val)


def testDb(rdsi):
    print(rdsi.query_name("elantris"))


if __name__ == "__main__":
    access_token = load_configuration()["ACCESS_TOKEN"]
    dbi = DropboxInterface(access_token)
    # run(dbi)
    db_name = load_configuration()["db_name"]
    db_password = load_configuration()["db_password"]
    db_user = load_configuration()["db_user"]
    rds_host = load_configuration()["rds_host"]

    rdsi = RDSInterface(rds_host, db_user, db_password, db_name)
    testDb(rdsi)
