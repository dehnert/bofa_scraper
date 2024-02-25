#!/usr/bin/env python3

import csv
import sys

def merge_csv(files):
    """Merge several CSV files together

    Take the union of the columns across all files, then concatenate the rows
    (treated as sequences of dicts).

    I haven't tested with different columns in different files, but presumably
    it will either error or fill in missing columns.
    """
    rows = []
    # I want to preserve header order, and it seems like dicts preserve order
    # and sets don't, so we use a dict here
    cols_all = dict()
    for filename in files:
        with open(filename, 'r') as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                rows.append(row)
            print(reader.fieldnames, file=sys.stderr)
            for col in reader.fieldnames: cols_all[col] = None
    print(cols_all, file=sys.stderr)

    writer = csv.DictWriter(sys.stdout, cols_all.keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

if __name__ == '__main__':
    merge_csv(sys.argv[1:])
