#! /usr/bin/env python3
from glob import glob
import subprocess

if __name__ == "__main__":
    log_files = glob("*.log")
    res_files = glob("*.res")

    print(f"Found {len(log_files)} .log files and {len(res_files)} .res files")

    log_files_no_suffix = [file.replace(".log", "") for file in log_files]
    res_files_no_suffix = [file.replace(".res", "") for file in res_files]

    no_res = list(set(log_files_no_suffix) - set(res_files_no_suffix))
    no_res.sort()

    print(f"Found {len(no_res)} simulations without a .res file:")

    for i, file in enumerate(no_res):
        print(f"\t{file}.log")

    remove_input = input("Remove .log files without a .res file (Y/N)? ")

    if remove_input.lower() == "y":
        for file in no_res:
            subprocess.call(["rm", file + ".log"])
