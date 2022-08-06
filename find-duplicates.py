#!/usr/bin/env python3
import sys, os, filecmp, argparse

# Arguments
parser = argparse.ArgumentParser(description='Find duplicate files using their MD5 hashes.')
parser.add_argument('directories', metavar='DIR', type=str, nargs='+',
                    help='directories to search recursively')
parser.add_argument('-d', '--delete', dest='delete', action='store_true',
                    help='delete the duplicate files (default false)')
args = parser.parse_args()


def md5(fname, chunk_size=1024):
    import hashlib
    hash = hashlib.md5()
    try:
        with open(fname, "rb") as f:
            chunk = f.read(chunk_size)
            while chunk:
                hash.update(chunk)
                chunk = f.read(chunk_size)
    except OSError as e:
        print("Warning: Error ({e}) while reading ({fname})".format(e=e, fname=fname))
        return None
    return hash.hexdigest()


sizes = {}
hashes = {}
duplicates = []

# Traverse all the files and store their size in a reverse index map
files_count = 0
for s in args.directories:
    if not (os.path.exists(s) and os.path.isdir(s)):
        print(f"Directory doesn't exist or not a directory: {s}")
        exit(1)
    for root, dirs, files in os.walk(s, topdown=True, onerror=None, followlinks=False):
        files_count += len(files)
        for f in files:
            file = os.path.join(root, f)
            size = os.stat(file).st_size
            if size not in sizes:
                sizes[size] = []
            sizes[size].append(file)
print("Traversed {} files".format(files_count))

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
        if hash is not None:
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
    assert len(group) > 1
    print("%r:" % (i + 1))
    for d in group:
        print("  %r" % (d))
    if args.delete:
        for d in group[1:]:
            os.remove(d)
            print("  Removed %r" % (d))
if not duplicates:
    print("No duplicates found")
