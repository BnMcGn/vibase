
import tempfile
import subprocess
import shutil
import csv
import argparse
import importlib


def extract_conn_from_module(module):
    for name in dir(module):
        if "cursor" in module[name]:
            return module[name]

def write_csv(fname, conn, table):
    cursor = conn.cursor()
    cursor.execute("select * from {};".format(table))
    writ = csv.writer(fname)
    writ.writerow([i[0] for i in cursor.description])
    writ.writerows(cursor)

def call_vim(target, vim=None):
    print("Waiting for VIM to exit")
    vim = vim if vim else shutil.which("vim")
    subprocess.run([vim, target])

def get_connection(args):
    if "module" in args:
        return extract_conn_from_module(import_module(args.module))
    else:
        raise (RuntimeError, "No connection source supplied")

def arguments():
    args = argparse.ArgumentParser(description="Edit the contents of a database table using the VIM editor")
    args.add_argument("table", help="The table to edit")
    args.add_argument("-m", "--module", help="Supply a python module containing a connection object")
    return args

def main():
    args = arguments().parse_args()

    tfile = tempfile.NamedTempFile()
    conn = get_connection(args)
    #FIXME: check table exists
    #FIXME: check table has pkey
    write_csv(tfile.name, conn, args.table)
    call_vim(tfile.name)


if __name__ == "__main__":
    main()
