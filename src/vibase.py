
import sys
import os
import tempfile
import subprocess
import shutil
import csv
import sqlite3
import argparse
from importlib import import_module

from src.util import query_yes_no, query_options

def is_file_sqlite(fname):
    idstring = "SQLite format 3"
    with open(fname, 'r', errors='ignore') as fh:
        line = fh.readline()
        return line.startswith(idstring)

def extract_conn_from_module(module):
    for x in module.__dict__.values()
        if hasattr(x, "cursor"):
            return x
    raise (RuntimeError, "Couldn't find connection")

def write_csv(fname, conn, table):
    cursor = conn.cursor()
    cursor.execute("select * from {};".format(table))
    writ = csv.writer(fname)
    headers = [i[0] for i in cursor.description]
    writ.writerow(headers)
    for row in cursor:
        writ.writerow(["NULL" if x == None else x for x in row])
    #writ.writerows(cursor)
    return headers

def call_vim(target, vim=None):
    print("Waiting for VIM to exit")
    vim = vim if vim else shutil.which("vim")
    subprocess.run([vim, target])

def get_connection(args):
    if "connection" in args and os.path.exists(args.connection):
        if is_file_sqlite(args.connection):
            return sqlite3.connect(args.connection)
        else:
            module = args.connection
            if module.endswith(".py"):
                module = module[:-3]
            elif module.endswith(".pyc"):
                module = module[:-4]
            conn = extract_conn_from_module(import_module(module))
            configure_for_connection(conn)
            return conn
    else:
        raise (RuntimeError, "No connection source supplied")

param_char = "?"
def sql_param_char():
    return param_char

def configure_for_connection(conn):
    global param_char
    "Attempt to detect type of DB, and set up some options accordingly"
    #FIXME: Better detection method?
    if "psycopg2" in repr(type(conn)):
        param_char = "%s"

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

def get_extra_lines(refstream, editstream):
    ref = list(refstream)
    if len(ref):
        raise (RuntimeError, "Edited CSV is too short! Did you attempt to delete a record by removing a line? Leave an empty line in place of a record to delete it.")
    # At this point the edit stream should be empty, but we may allow 
    # insertions in future, so return the extras.
    return list(editstream)

def decide_action(rows):
    refs = []
    edits = []
    dels = []
    for ref, edit in rows:
        if edit:
            refs.append(ref)
            edits.append(edit)
        else:
            dels.append(ref)
    return {'reference': refs, 'edit': edits, 'delete': dels}

def make_update_sql(table, headers, old_data, upd_data):
    vclause = []
    wclause = []
    old = []
    upd = []
    for col, odat, udat in zip(headers, old_data, upd_data):
        odat = null_to_none(odat)
        udat = null_to_none(udat)
        vclause.append(", ")
        vclause.append("{} = {}".format(col, sql_param_char()))
        wclause.append(" and ")
        if odat:
            wclause.append("{} = {}".format(col, sql_param_char()))
            old.append(odat)
        else:
            wclause.append("{} is null".format(col))
        upd.append(udat)
    vclause = "".join(vclause[1:])
    wclause = "".join(wclause[1:])
    query = "update {} set {} where {}".format(table, vclause, wclause)
    return query, upd + old

def null_to_none(item):
    return None if item == "NULL" else item
    
def do_updates(table, headers, reference, edited, conn):
    try:
        cur = conn.cursor()
        for r, e in zip(reference, edited):
            query, params = make_update_sql(table, headers, r, e)
            cur.execute(query, params)
        conn.commit()
        print (cur.rowcount, "Rows updated")
    except Exception as error:
        raise RuntimeError("DB error:", error)
    finally:
        cur.close()

def make_delete_sql(table, headers, data):
    wclause = []
    out = []
    for col, dat in zip(headers, data):
        dat = null_to_none(dat)
        wclause.append(" and ")
        if dat:
            wclause.append("{} = {}".format(col, sql_param_char()))
            out.append(dat)
        else:
            wclause.append("{} is null".format(col))
    wclause = "".join(wclause[1:])
    sql = "delete from {} where {}".format(table, wclause)
    return sql, out

def do_deletes(table, headers, deletes, conn):
    try:
        cur = conn.cursor()
        for dl in deletes:
            query, params = make_delete_sql(table, headers, dl)
            cur.execute(query, params)
        conn.commit()
        print (cur.rowcount, "Rows deleted")
    except Exception as error:
        raise RuntimeError("DB error:", error)
    finally:
        cur.close()

def process_changes(reffile, editfile, conn, table, headers):

    with open(editfile.name, "r", newline="") as eh, \
        open(reffile.name, "r", newline="") as rh:
        res = decide_action(filter_changed_rows(rh, eh))
        extras = get_extra_lines(rh, eh)
        if len(extras):
            raise (RuntimeError, "Extra lines found: Insertion not currently supported")
    upd_count = len(res['reference'])
    del_count = len(res['delete'])
    if upd_count:
        print("{} record(s) to update".format(upd_count))
    if del_count:
        print("{} record(s) to delete".format(del_count))
    if upd_count or del_count:
        if query_yes_no("Proceed?") == "yes":
            if upd_count:
                do_updates(table, headers, res['reference'], res['edit'], conn)
            if del_count:
                do_deletes(table, headers, res['delete'], conn)
        else:
            print ("Changes discarded")
    else:
        print ("No changes found")

def arguments():
    args = argparse.ArgumentParser(description="Edit the contents of a database table using the VIM editor")
    args.add_argument("connection", help="Supply a database. This can be a sqlite database file, or it can be a python module containing a connection object.")
    args.add_argument("table", help="The table to edit")
    return args

def main():
    args = arguments().parse_args()

    sys.path.insert(0, os.getcwd())
    conn = get_connection(args)
    #FIXME: check table exists
    headers = None
    editfile = tempfile.NamedTemporaryFile()
    with open(editfile.name, "w", newline='') as cfile: 
        headers = write_csv(cfile, conn, args.table)
    reffile = tempfile.NamedTemporaryFile()
    shutil.copy(editfile.name, reffile.name)
    
    call_vim(editfile.name)
    while True:
        try:
            process_changes(reffile, editfile, conn, args.table, headers)
            break
        except Exception as err:
            print ("Failed to save changes: ", err)
            q = "(C)ancel, (r)etry save, (e)dit the file again?"
            cmd = query_options(q, ("c", "r", "e"))
            if cmd == 'c':
                print ("Changes cancelled")
                break
            elif cmd == 'r':
                continue
            elif cmd == 'e':
                call_vim(editfile.name)
            else:
                raise ValueError("Not a command")


if __name__ == "__main__":
    main()
