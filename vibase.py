
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
    headers = [i[0] for i in cursor.description]
    writ.writerow(headers)
    writ.writerows(cursor)
    return headers

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

def make_update_sql(table, headers):
    vclause = []
    wclause = []
    for col in headers:
        vclause.append(", ")
        vclause.append("{} = ?".format(col))
        wclause.append(" and ")
        wclause.append("{} = ?".format(col))
    vclause = "".join(vclause[1:])
    wclause = "".join(wclause[1:])
    return "update {} set {} where {}".format(table, vclause, wclause)
    
def do_updates(table, headers, reference, edited, conn):
    query = make_update_sql(table, headers)

    data = (e + r for r, e in zip(reference, edited))

    try:
        cur = conn.cursor()
        print (query, list(data))
        #cur.executemany(query, data)
        #FIXME: should happen further up?
        conn.commit()
        print (cur.rowcount, "Rows updated")
    except Exception as error:
        raise RuntimeError("DB error:", error)
    finally:
        cur.close()

def make_delete_sql(table, headers):
    wclause = []
    for col in headers:
        wclause.append(" and ")
        wclause.append("{} = ?".format(col))
    wclause = "".join(wclause[1:])
    return "delete from {} where {}".format(table, wclause)

def do_deletes(table, headers, deletes, conn):
    query = make_delete_sql(table, headers)

    try:
        cur = conn.cursor()
        print (query, list(deletes))
        #cur.executemany(query, deletes)
        #FIXME: should happen further up?
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
    #FIXME: Ask before running, with report.
    do_updates(table, headers, res['reference'], res['edit'], conn)
    do_deletes(table, headers, res['delete'], conn)

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
    headers = None
    editfile = tempfile.NamedTemporaryFile()
    with open(editfile.name, "w", newline='') as cfile: 
        headers = write_csv(cfile, conn, args.table)
    reffile = tempfile.NamedTemporaryFile()
    shutil.copy(editfile.name, reffile.name)

    call_vim(editfile.name)

    process_changes(reffile, editfile, conn, args.table, headers)
    



if __name__ == "__main__":
    main()
