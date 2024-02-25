#!/bin/sh

set -eu

# No `set -f` because we need globbing

for file in "$@"; do
    echo "Processing $file"
    ./merge_csv.py "$file".transaction_period*.csv > "$file".merged.csv
done
