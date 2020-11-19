# Vibase

Edit a database table using the VIM editor.

# Description

Inspired by [vidir](https://github.com/trapd00r/vidir), vibase allows you to quickly edit the data in your databases using the legendary VIM editor. 

Call vibase from the command line, and it will load the specified table into a temporary CSV file. Once you have finished editing the file, it will compare the differences and run the appropriate Update or Delete queries.

WARNING: This version of vibase is in early development. It is young. It's hungry. IT WANTS TO EAT YOUR DATA!!! Just so you know...

# Usage

    > vibase --module [module] [table] 

At this time vibase only supports loading database connections through a python module. The first DBI connection found in the top level of the supplied module will be used. The module should be loadable by python 3.

To connect to a postgresql database named cookiejar, you might create a file cjar.py:

    from psycopg2 import connect

    conn = connect(host="localhost", \
                   database="cookiejar", \
                   user="me",
                   password="totally_unguessable")

You may then edit the ingredients table:

    > vibase --module cjar ingredients

# Author

Ben McGunigle bnmcgn (at) gmail.com

# License

Apache License version 2.0
