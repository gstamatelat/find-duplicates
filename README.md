# Find Duplicates

Python 3 script to find duplicate files in a directory tree.

Usage: `./find-duplicates /path/to/dir1 /path/to/dir2 ...`

Files are first filtered based on their size, then on their MD5 hash and finally a pairwise byte comparison is performed.
