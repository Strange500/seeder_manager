
import json, os, shutil, threading, time
from qbittorrentapi import Client
from datetime import  datetime, timedelta
from copy import deepcopy
from typing import Tuple, Dict
def parse_conf(conf_file_path: str):
    conf = {}
    with open(conf_file_path, "r") as f:
        for lines in f:
            if not lines[0] in ["#", "\n", ""]:
                if not " = " in lines:
                    raise Exception(f"{conf_file_path} malformed at line {lines}")
                lines = lines.split(" = ")
                key = lines[0]
                if lines[1].replace("\n", "") == "FALSE":
                    value = False
                elif lines[1].replace("\n", "") == "TRUE":
                    value = True
                elif lines[1].replace("\n", "") == "NONE":
                    value = "NONE"
                else:
                    if key == "seed_directory":
                        value = lines[1].replace("\n", "").split(" ")
                    else:
                        value = lines[1].replace("\n", "").split(" ")[0]

                conf[key] = value
    return conf

def stop_torrent_with_file_name(qbittorrent_host, port, username, password, file_name):
    # Connect to qBittorrent
    qb = Client(host=qbittorrent_host, port=port, username=username, password=password)

    # Get the list of torrents
    torrents = qb.torrents.info()

    # Iterate through the torrents and find the one containing the specified file name
    for torrent in torrents:
        torrent_name = torrent['name']
        if file_name in torrent_name:
            torrent_hash = torrent['hash']
            qb.torrents.pause(torrent_hash)
            print("Torrent stopped:", torrent_name)
            return

    print("Torrent not found:", file_name)

def safe_copy(src, dst, retry_delay=10):
    """
    Safely moves a file from the source to the destination path.

    Args:
        src (str): The source file path.
        dst (str): The destination file path.
        max_retries (int, optional): Maximum number of retries in case of PermissionError or RuntimeError. Defaults to 2.
        retry_delay (int, optional): Delay in seconds between retries. Defaults to 1.

    Returns:
        bool: True if the file was successfully moved and removed from the source, False otherwise.

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If the source file is not a video file.

    """
    if not os.path.isfile(src):
        raise FileNotFoundError(f"{src} is not a file")

    retries = 0
    while os.path.basename(src) not in os.listdir(dst):
        try:
            print(f"cpy {src}")
            shutil.copy(src, dst)
            print(f"end copy {src}")
        except (PermissionError, RuntimeError):
            retries += 1
            time.sleep(retry_delay)

    return False
def parse_date(date:str):
    date = date.split("-")
    return {"year":int(date[0]), "month":int(date[1]), "day":int(date[2])}
def get_directory_size(directory):
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)

    return total_size

def get_file_paths(directory):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_paths.append(file_path)
    return file_paths

def check_json(path):
    """
    Checks if the given file is a valid JSON file.

    Args:
        path (str): The path to the file.

    Returns:
        bool: True if the file is a valid JSON file, False otherwise.

    Raises:
        FileNotFoundError: If the file does not exist.

    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{path} does not exist")

    if "json" not in path:
        return True

    try:
        with open(path, "r", encoding="utf-8") as file:
            json.load(file)
        return True
    except json.decoder.JSONDecodeError:
        return False

def gen_id(list_id: list):
    n_id = 0
    while n_id in list_id:
        n_id +=1
    return n_id
def save_upload(target_file: str):
    path = os.path.join(os.getcwd(), target_file)
    done = False
    while not done:
        try:
            json.dump(Manager.upload_data, open(path, "w"), indent=5)
            done = True
        except PermissionError:
            time.sleep(1)
            pass

def already_scan(path:str):
    for upload in Manager.upload_data:
        if Manager.upload_data[upload]["path"] == path:
            return True
    return False
def get_first_parent_directory(file_path):
    directory, filename = os.path.split(file_path)
    if len(filename) > 10:
        directory, filename = os.path.split(file_path)
        p = get_first_parent_directory(directory)
    else:
        p = filename
    parent_directory = p
    return parent_directory
def transfert_upload(path:str):
    dst = os.path.join(Manager.redirect_dir, get_first_parent_directory(path))
    os.makedirs(dst, exist_ok=True)
    safe_copy(path, dst)

def check_upload():
    temp = deepcopy(Manager.upload_data)
    for up in temp:
        path = Manager.upload_data[up]['path']
        if not (os.path.isfile(path) or os.path.isdir(path)):
            Manager.upload_data.pop(up)
            save_upload(Manager.upload_data_file)
class Manager:
    conf_file : str
    upload_data_file : str
    conf : dict
    upload_data : dict
    max_size : int
    conf_file = "manager.conf"
    upload_data_file = "upload_data.json"
    conf = parse_conf(conf_file)
    if not os.path.isfile(upload_data_file) or not check_json(upload_data_file):
        json.dump({}, open(upload_data_file, "w"))
    upload_data = json.load(open(upload_data_file, "r"))

    scan_dir_path = conf["seed_directory"]
    redirect_dir = conf["redirect_directory"]
    max_size = int(conf["number_of_bit_max"])
    day_delay = int(conf["day_delay"])

    qbit_host = conf["qbittorrent_api_host"]
    qbit_port = int(conf["qbittorrent_api_port"])
    qbit_user = conf["username"]
    qbit_pass = conf["password"]

    def delete(id:int):
        if Manager.upload_data.get(str(id), None) is None:
            return
        else:
            Manager.upload_data.pop(str(id))

    def total_size(nothing = False):
        total_size = 0
        for key in Manager.upload_data:
            total_size += Manager.upload_data[key]["size"]
        return total_size

    def add_upload(path:str):
        if os.path.isfile(path):
            size = os.path.getsize(path)
        elif os.path.isdir(path):
            size = get_directory_size(path)
        else:
            raise FileNotFoundError
        start_date = datetime.now().strftime("%Y-%m-%d")
        limit_date = (datetime.now() + timedelta(days=Manager.day_delay)).strftime("%Y-%m-%d")
        up_id = gen_id([int(i) for i in Manager.upload_data])
        Manager.upload_data[up_id] = {"size": size,
                                      "start_date": start_date,
                                      "limit_date": limit_date,
                                      "path": path}

        save_upload(Manager.upload_data_file)
        if os.path.isfile(path):
            transfert_upload(path)
        elif os.path.isdir(path):
            for file in get_file_paths(path):
                transfert_upload(file)

    def scan_dir(target_dir:str):
        for file in os.listdir(target_dir):
            if not already_scan(os.path.join(target_dir, file)):
                print(file)
                Manager.add_upload(os.path.join(target_dir, file))

    def get_older(tkt=None):
        id_up, info = datetime.now(), {}
        for upload in Manager.upload_data:
            start = Manager.upload_data[upload]['start_date']
            start = datetime(**parse_date(start))
            if start < datetime.now():
                id_up, info = upload, Manager.upload_data[upload]
        return id_up, info




    def update_uplaod(tkt = False):
        temp = deepcopy(Manager.upload_data)
        for upload in temp:
            limit_date = Manager.upload_data[upload]['limit_date']
            limit_date = datetime(**parse_date(limit_date))
            if limit_date < datetime.now():
                Upload(Manager.upload_data[upload]['path'], Manager.upload_data[upload], int(upload)).delete_upload()
        if Manager.total_size() > Manager.max_size:
            id_up, info = Manager.get_older()
            Upload(info['path'], info, int(id_up)).delete_upload()

        save_upload(Manager.upload_data_file)







class Upload:
    def __init__(self, path: str, info: dict, id_up:int):
        self.path = path
        self.limit_date = info["limit_date"]
        self.start_date = info["start_date"]
        self.size = info["size"]
        self.id = id_up


    def delete_upload(self):
        stop_torrent_with_file_name(Manager.qbit_host, Manager.qbit_port, Manager.qbit_user, Manager.qbit_pass, os.path.basename(self.path))
        if os.path.isfile(self.path):
            os.remove(self.path)
        if os.path.isdir(self.path):
            shutil.rmtree(self.path)
        Manager.delete(self.id)


