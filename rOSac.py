#!/usr/bin/env python3
"""
A simple python program for collecting useful artifacts from a Mikrotik router.
Hopefully useful in incident response.

author: @linkavych
date: 2022-09-07
version: 0.1
"""
import os
import pathlib
import tarfile
import shutil
from datetime import datetime

# For SSH
from fabric import Connection

# CLI stuff
import typer

def banner():
   print("""
                     _            _____ _____    ___       _   _  __           _     _____       _ _           _             
                    | |          |  _  /  ___|  / _ \     | | (_)/ _|         | |   /  __ \     | | |         | |            
     _ __ ___  _   _| |_ ___ _ __| | | \ `--.  / /_\ \_ __| |_ _| |_ __ _  ___| |_  | /  \/ ___ | | | ___  ___| |_ ___  _ __ 
    | '__/ _ \| | | | __/ _ \ '__| | | |`--. \ |  _  | '__| __| |  _/ _` |/ __| __| | |    / _ \| | |/ _ \/ __| __/ _ \| '__|
    | | | (_) | |_| | ||  __/ |  \ \_/ /\__/ / | | | | |  | |_| | || (_| | (__| |_  | \__/\ (_) | | |  __/ (__| || (_) | |   
    |_|  \___/ \__,_|\__\___|_|   \___/\____/  \_| |_/_|   \__|_|_| \__,_|\___|\__|  \____/\___/|_|_|\___|\___|\__\___/|_|   

                                author: @linkavych
                                updated: 2022-09-07
         """)

def get_connection(ip: str, username: str, keyfile: str):
    """
    Establish a connection with the provided router.

    Return a connection object.
    """
    c = Connection(ip, user=username, connect_kwargs={"key_filename": keyfile})

    return c


def get_commands(cfiles: list):
    """
    Open the given command file, read the lines, and return a list of commands.

    For now, command files are plain text files with commands separated by newlines.

    Returns a dictionary
        Key: name of the command type (for printing and organization)
        Value: a list of commands
    """
    cmds = {}

    for cf in cfiles:
        with open(cf, "r", encoding="utf-8") as fd:
            data = fd.readlines()
            for line in data:
                if cmds.get(cf.stem) is None:
                    cmds[cf.stem] = [line]
                else:
                    cmds[cf.stem].append(line)

    return cmds


def get_cmd_file(path: str):
    """
    Get a list of all files from which to gather commands
    If no directory path provided, assume current directory.

    return a list of files to open
    """
    dir_path = path
    d = pathlib.Path(dir_path)

    return [x for x in d.iterdir() if x.is_file()]


def run_commands(connection, cmds: list):
    """
    Run the selected commands against the target system

    Return the results to stdout...
    """
    p = pathlib.Path("output/")
    p.mkdir(parents=True, exist_ok=True)

    for cmd in cmds:
        fn = f"{cmd}_output.txt"
        fp = p / fn
        print(
            f"[+] Executing {len(cmds[cmd])} commands from: {cmd} on target router..."
        )

        with fp.open("w", encoding="utf-8") as f:
            print("#" * 40, file=f)
            print(f"{cmd.center(40)}", file=f)
            print("#" * 40, file=f)
            try:
                for i in cmds[cmd]:
                    print(f"[+] Command: {i}", file=f)
                    res = connection.run(i, hide="both")
                    print(res, file=f)
            except:
                continue

    return


def generate_files(connection):
    """
    Parsing some results to generate a list of file names on the device

    This is not a clean solution - very hacky, but it works for now

    This will potentially miss files if they are in subfolders...TODO!
    """
    print(f"[+] Gathering filenames from router...")
    results = connection.run("/file print", hide="both")
    with open("temp", "w", encoding="utf-8") as fp:
        print(results, file=fp)

    with open("temp", "r", encoding="utf-8") as f:
        data = f.readlines()
        data = data[4:-1]

    new_data = [x.split() for x in data]
    files = []

    for x in new_data:
        try:
            files.append(x[1])
        except:
            continue

    os.remove("temp")
    print("[+] Cleaning up temporary files...")

    return files


def download_files(connection):
    """
    Function to download all files store on a mikrotike router

    Write each file to local disk in dir: output/files/
    """
    pathlib.Path("output/files").mkdir(parents=True, exist_ok=True)

    files = generate_files(connection)

    print(f"[+] Downloading {len(files)} from target router...")

    for file in files:
        try:
            connection.get(file, local="output/files/")
        except:
            continue

    return


def backup_router(connection):
    """
    Make a backup of the router for artifact collection
    Download the backup to local filesystem
    """
    print("[+] Backing up the router and downloading...")

    connection.run("/system backup save name=rtrbackup", hide="both")
    pathlib.Path("output/files/backup").mkdir(parents=True, exist_ok=True)
    connection.get("rtrbackup.backup", local="output/files/backup/")
    connection.run("/file remove rtrbackup.backup", hide="both")

    return


def get_config(connection):
    """
    Make a backup of the router's configuration file and download it.
    """
    print("[+] creating a configuration backup and downloading...")

    pathlib.Path("output/files/config").mkdir(parents=True, exist_ok=True)
    connection.run("/export file=config", hide="both")
    connection.get("config.rsc", local="output/files/config/")
    connection.run("/file remove config.rsc", hide="both")


def compress_output():
    """
    Compress the results of this script into a .tar.gz format.
    Save result in the current directory and remove all other output.

    UTC timestamp output
    """
    print("[+] Compressing files...")
    print(f"[+] Timestamp is in UTC: {datetime.utcnow()}...")
    ftime = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = "output_" + ftime

    with tarfile.open(filename + ".tar.gz", mode="w:gz") as a:
        a.add("output/", recursive=True)

    # Remove file structure; leaving only compressed files
    shutil.rmtree("output/")

    return


def main(
    ip: str = typer.Option(..., help="The IP address for the targeted router."),
    username: str = typer.Option(..., help="The username for the targeted router."),
    keyfile: str = typer.Option(..., help="The file path to where the ssh key is located."),
    cmdpath: str = typer.Option(
        ..., help="Path to location where commands files are located."
    ),
    get_files: bool = typer.Option(
        False, help="Download all files from target router to local disk."
    ),
    sys_backup: bool = typer.Option(
        False, help="Make a system level backup on the router."
    ),
    conf_backup: bool = typer.Option(
        False, help="Create a backup of the router configuration for download."
    ),
):
    """
    routerOS Artifact Collector

    Collect relevant forensic artifacts from routerOS systems. This is a live-response tool
    and may make changes on the target system. 

    Still a work-in-progress:

    TODO:
        1. keyfile made optional with choice to use a password
        2. Add ability to use a list of IP addresses

    """
    banner()

    c = get_connection(ip, username, keyfile)

    cmdfiles = get_cmd_file(cmdpath)

    cmds = get_commands(cmdfiles)

    run_commands(c, cmds)

    if get_files:
        download_files(c)

    if sys_backup:
        backup_router(c)

    if conf_backup:
        get_config(c)

    compress_output()

    return


if __name__ == "__main__":
    typer.run(main)
