
import tempfile
import subprocess
import shutil
import csv
import argparse
from importlib import import_module


def extract_conn_from_module(module):
    for x in module.__dict__.values():
        if hasattr(x, "cursor"):
            return x

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

def filter_changed_rows(refstream, editstream):
    #Check the header row
    try:
        rhead = next(refstream)
        ehead = next(editstream)
    except StopIteration:
        raise (RuntimeError, "Nothing found in CSV file")
    if not rhead == ehead:
        raise (RuntimeError, "Header row should not be edited")
    for ref, ed in zip(csv.reader(refstream), csv.reader(editstream)):
        if not ref == ed:
            yield (ref, ed)

def arguments():
    args = argparse.ArgumentParser(description="Edit the contents of a database table using the VIM editor")
    args.add_argument("table", help="The table to edit")
    args.add_argument("-m", "--module", help="Supply a python module containing a connection object")
    return args

def main():
    args = arguments().parse_args()

    conn = get_connection(args)
    #FIXME: check table exists
    #FIXME: check table has pkey
    editfile = tempfile.NamedTemporaryFile()
    with open(editfile.name, "w", newline='') as cfile: 
        write_csv(cfile, conn, args.table)
    reffile = tempfile.NamedTemporaryFile()
    shutil.copy(editfile.name, reffile.name)

    call_vim(editfile.name)

    with open(editfile.name, "r", newline="") as eh, \
        open(reffile.name, "r", newline="") as rh:
        res = filter_changed_rows(rh, eh)
        print(list(res))



if __name__ == "__main__":
    main()
