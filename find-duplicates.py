#!/usr/bin/env python3
import sys, os, hashlib, filecmp


def md5(fname, chunk_size=1024):
    hash = hashlib.md5()
    with open(fname, "rb") as f:
        chunk = f.read(chunk_size)
        while chunk:
            hash.update(chunk)
            chunk = f.read(chunk_size)
    return hash.hexdigest()


sizes = {}
hashes = {}
duplicates = []

# Traverse all the files and store their size in a reverse index map
for s in sys.argv[1:]:
    for root, dirs, files in os.walk(s, topdown=True, onerror=None, followlinks=False):
        for f in files:
            file = os.path.join(root, f)
            size = os.stat(file).st_size
            if size not in sizes:
                sizes[size] = []
            sizes[size].append(file)

# Remove empty files from the size map
if 0 in sizes:
    del sizes[0]

# Remove files with unique sizes from the size map
for (key, value) in list(sizes.items()):
    if len(value) == 1:
        del sizes[key]

# Traverse the size map and enrich it with hashes
for (size, files) in sizes.items():
    for file in files:
        hash = md5(file)
        tuple = (size, hash)
        if tuple not in hashes:
            hashes[tuple] = []
        hashes[tuple].append(file)

# Remove files with unique (size, hash) tuple in hash map
for (key, value) in list(hashes.items()):
    if len(value) == 1:
        del hashes[key]

# Compare file pairs
for possible_list in hashes.values():
    while possible_list:
        first = possible_list[0]
        copy = [first]
        for other in possible_list[1:]:
            if filecmp.cmp(first, other, shallow=False):
                copy.append(other)
        for c in copy:
            possible_list.remove(c)
        duplicates.append(copy)

# Print duplicates
for i, group in enumerate(duplicates):
    print("%r:" % (i + 1))
    for d in group:
        print("  %r" % (d))
