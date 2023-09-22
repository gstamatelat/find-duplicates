#!/usr/bin/env python3
# import sys
import os
import filecmp
import argparse
# import json
from collections import defaultdict
import hashlib

try:
    import xxhash
except ImportError:
    xxhash = None

# Arguments
parser = argparse.ArgumentParser(description='Find duplicate files using their hashes.')

parser.add_argument('directories', metavar='DIR', type=str, nargs='+',
                    help='directories to search recursively')
parser.add_argument('-d', '--delete', dest='delete', action='store_true',
                    help='delete the duplicate files (default false)')
# parser.add_argument('-j', '--json', dest='json', action='store_true',
#                     help='output json format for duplicate files (default false)')
parser.add_argument('-l', '--hardlinks', dest='hlinks', action='store_true',
                    help='include hardlinked files (default false)')
parser.add_argument('--md5', dest='use_md5', action=argparse.BooleanOptionalAction,
                    default=False,
                    help='use md5 hash')

parser.add_argument('--min', dest='min_size', default='0', type=int,
                    help='minimum file size')
parser.add_argument('--max', dest='max_size', default='0', type=int,
                    help='maximum file size')

parser.add_argument('--verbose', '-v', action='count', default=0,
                    help='Be more Verbose')

args = parser.parse_args()


# https://stackoverflow.com/questions/75676231/how-to-prevent-filling-up-memory-when-hashing-large-files-with-xxhash
def read_in_chunks(file_object, chunk_size=4096):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


# mmap can speed this but it not cross OS compat
def get_xxhash(fname):
    h = xxhash.xxh3_128(seed=0)
    with open(fname, 'rb') as input_file:
        for chunk in read_in_chunks(input_file):
            h.update(chunk)
    return h.hexdigest()


# mmap can speed this but it not cross OS compat
def get_md5(fname, chunk_size=1024):
    mhash = hashlib.md5()
    try:
        with open(fname, "rb") as fd:
            chunk = fd.read(chunk_size)
            while chunk:
                mhash.update(chunk)
                chunk = fd.read(chunk_size)
    except OSError as e:
        print(f"Warning: Error ({e}) while reading ({fname})")
        return None
    return mhash.hexdigest()


# should add argParse options for these (eventually)
file_excludes = [
]

dir_excludes = [
    ".AppleDB",
    ".AppleDesktop",
    ".AppleDouble",
    ".RECYCLER",
    ".Spotlight-V100",
    ".thumbs",
    '.DS_Store',
    '.Trash',
    '.git',
    '.svn',
    'CVS',
    'Network Trash Folder',
    'RCS',
    'SCCS',
    '__pycache__',
]

sizes = defaultdict(list)
hashes = defaultdict(list)
duplicates = []


# Traverse all the files and store their size in a reverse index map
def traverse_files():
    files_count = 0
    skipped_max_size = 0
    skipped_min_size = 0
    for s in args.directories:

        inodes = []

        if not (os.path.exists(s) and os.path.isdir(s)):
            print(f"Directory doesn't exist or not a directory: {s} (Skipping)")
            # exit(1)
            continue

        for root, dirs, files in os.walk(s, topdown=True, onerror=None, followlinks=False):

            # Skip excluded files and directories
            dirs[:] = [de for de in dirs if de not in dir_excludes and de[-1] != '~']
            files[:] = [de for de in files if de not in file_excludes and de[-1] != '~']

            files_count += len(files)
            for f in files:
                filen = os.path.join(root, f)

                # skip Symlinks
                if os.path.islink(filen):
                    continue

                # skip unreadable files
                if not os.access(filen, os.R_OK):
                    continue

                fn_st = os.stat(filen)
                size = fn_st.st_size

                # Filter zero lengthfiles and optionally small files
                if size == 0 or (args.min_size and size <= args.min_size):   # empty or small files
                    skipped_min_size += 1
                    continue

                # optionally filter Large files
                if args.max_size and size >= args.max_size:
                    skipped_max_size += 1
                    continue

                # Filter out Hardlinked files
                if fn_st.st_nlink > 1 and not args.hlinks:
                    fn_ino = fn_st.st_ino
                    if fn_ino in inodes:
                        if args.verbose > 2:
                            print(f"inode {fn_ino} {filen}")
                        continue
                    inodes.append(fn_ino)

                size = os.stat(filen).st_size

                sizes[size].append(filen)

    print(f"Traversed {files_count} files")

    if args.verbose and args.min_size:
        print(f"Min size skipped: {skipped_min_size}")
    if args.verbose and args.max_size:
        print(f"Min size skipped: {skipped_max_size}")

    # Remove empty files from the size map
    if 0 in sizes:
        del sizes[0]

    # Remove files with unique sizes from the size map
    for (key, value) in list(sizes.items()):
        if len(value) == 1:
            del sizes[key]


# Traverse the size map and enrich it with hashes
def gen_hashes():

    if xxhash is None or args.use_md5:
        get_hash = get_md5
    else:
        get_hash = get_xxhash

    if args.verbose > 1:
        if get_hash is get_xxhash:
            print("Using xxhash")
        else:
            print("Using md5")

    for (size, files) in sizes.items():
        for file in files:
            f_hash = get_hash(file)
            if f_hash is not None:
                f_tuple = (size, f_hash)
                if f_tuple not in hashes:
                    hashes[f_tuple] = []
                hashes[f_tuple].append(file)

    # Remove files with unique (size, hash) tuple in hash map
    for (key, value) in list(hashes.items()):
        if len(value) == 1:
            del hashes[key]


def do_filecmp():
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


if __name__ == '__main__':

    traverse_files()

    gen_hashes()

    do_filecmp()

    # if args.json:  # Generate a Json report
    #     json.dump(duplicates, sys.stdout, indent=4)
    #     # print(json.dumps(duplicates, indent=4))
    #     sys.exit(0)

    # Print duplicates
    for i, group in enumerate(duplicates):
        assert len(group) > 1
        print(f"{i + 1}:")
        for d in group:
            print(f"  {d}")
        if args.delete:
            for d in group[1:]:
                os.remove(d)
                print(f"  Removed {d}")

    if not duplicates:
        print("No duplicates found")
