from lib import *
import time

if __name__ == "__main__":
    while True:
        for dir in Manager.scan_dir_path:
            Manager.scan_dir(dir)
        Manager.update_uplaod()
        check_upload()
        time.sleep(1)

    print("ok")
