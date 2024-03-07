
# Changelog


## TODO

* Attempt to report time spent writing to database more accurately.
* Report on updated column of prefixes table, eg.

    SELECT min(updated) FROM prefixes;
    SELECT max(updated) FROM prefixes;
    SELECT avg(updated) FROM prefixes;
    SELECT updated FROM prefixes ORDER BY updated
        LIMIT 1 OFFSET (SELECT count(*) FROM prefixes) / 2;

* Update existing database:
    - Choose prefix (oldest? random?) and download its passwords.
    - Update, create (and delete?) rows in passwords table.
    - Repeat... FOREVER!

* Use Ned Bachelder's project template


## v0.3

* Capture user and system shutdown commands more gracefully.
* Print and log summary of program execution before exit.


## v0.2

* Display progress on terminal during download.
* Speed up database writes by enabling SQLite3 PRAGMAs
* Use log file parallel to database file.


## v0.1

* Basic functionality working: Download of missing password hashes from API
  and insertion of same into SQLite3 database.
