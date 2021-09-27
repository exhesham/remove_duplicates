from os import listdir
from os.path import isfile, join
import os
import hashlib
import re
import json

load_from_cache = True
OUTPUT_DIR = '.\\output'

files_dir = 'D:\\'
recycle_bin = 'C:\\Users\\Hesham Asus\\Desktop\\dups'

FILES_IN_DIR_CACHE_NAME = 'files_to_process - ' + hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
FILES_HASHES_CACHE_NAME = 'files_hashes - ' + hashlib.sha256(files_dir.encode('utf-8')).hexdigest()


def read_text_file(filename):
    file_lines = []
    if not os.path.isfile(os.path.join(OUTPUT_DIR, filename)):
        return None

    with open(os.path.join(OUTPUT_DIR, filename), "r", encoding="utf-8") as f:
        file_content = f.readlines()
        for line in file_content:
            file_lines.append(line.strip())
    return file_lines


def append_to_file(line, filename):
    line = line.encode('utf-8')
    # save list to file
    with open(os.path.join(OUTPUT_DIR, filename), 'a') as f:
        f.write("%s\n" % line)


def save_to_file(text, filename):
    # save list to file
    with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding="utf-8") as f:
        f.write(text)


def get_dir_all_files(path):
    if load_from_cache:
        cached_files = read_text_file(FILES_IN_DIR_CACHE_NAME)
        if cached_files is not None:
            print('found ', len(cached_files), ' cached files')
            return cached_files
    files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            files.append(os.path.join(r, file))
    print('found ', len(files), 'files')
    save_to_file('\n'.join(str(e) for e in files), FILES_IN_DIR_CACHE_NAME)
    return files


imported_hashes = None


# return hashes: { 'md5': [files], .... }
def get_files_hashes(files):
    def sha256sum(filename):
        try:
            h = hashlib.sha256()
            with open(filename, 'rb') as file:
                while True:
                    # Reading is buffered, so we can read smaller chunks.
                    chunk = file.read(h.block_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except:
            return None

    def hash_formatter(text):
        if text is not None:
            splitted = text.split('<@>')
            return {splitted[0]: splitted[1]}

    global imported_hashes
    if imported_hashes is None:
        text = read_text_file(FILES_HASHES_CACHE_NAME)
        if text is not None and len(text) > 0:
            imported_hashes = map(hash_formatter, text)
    hashes = {}
    index = 1
    total = len(files)
    for f in files:
        print(index, "/", total, "   ", f, end="\r")
        index = index + 1

        if imported_hashes is not None and f in imported_hashes:
            file_hash = imported_hashes[f]
        else:
            file_hash = sha256sum(f)
            append_to_file('%s<@>%s' % (file_hash, f), FILES_HASHES_CACHE_NAME)
        if file_hash is None:
            print('failed for hashing ', f)
        hashes.setdefault(file_hash, []).append(f)
    return hashes


def get_all_duplicates_according_to_hash(hashes):
    def choose_best_name(names):
        def hasIndexParenthesis(name):
            x = re.search("\(\d*\)", name)
            if x:
                return False
            return True

        result = list(filter(lambda x: hasIndexParenthesis(x), names))
        if len(result) == 0:
            # print("found zero on", names)
            return names[0]
        return result[0]

    all_dups = []
    for h in hashes:
        if len(hashes[h]) > 0:
            chosen_file = choose_best_name(hashes[h])
            for name in hashes[h]:
                if name != chosen_file and name.endswith(".mp3"):
                    all_dups.append(name)
    return all_dups


def get_all_similar_names(files):
    filenames_map = {}
    for f in files:
        filenames_map.setdefault(os.path.basename(f), []).append(f)
    dups = []
    for filename in filenames_map:
        if len(filenames_map[filename]) > 1:
            dups.extend(sorted(filenames_map[filename], key=len)[1:])
    return dups


def merge_duplicates(dupsnames, hashes):
    hashes_files = []
    hashes_files.extend(hashes)
    hashes_files.extend(dupsnames)
    return list(dict.fromkeys(hashes_files))


def move_to_recycle_bin(files, recycle_bin):
    for f in files:
        os.rename(f, os.path.join(recycle_bin, os.path.basename(f)))


if __name__ == '__main__':

    all_files = get_dir_all_files(files_dir)
    try:
        os.mkdir(OUTPUT_DIR)
    except:
        pass
    files_hash = get_files_hashes(all_files)
    get_all_hash_duplicates = get_all_duplicates_according_to_hash(files_hash)
    all_similar_names = get_all_similar_names(all_files)

    all_duplicate_files = merge_duplicates(all_similar_names, get_all_hash_duplicates)
    print('total duplicates to be deleted:', len(all_duplicate_files))
    move_to_recycle_bin(all_duplicate_files, recycle_bin)
    # print('will delete:')
    print("\n".join(sorted(all_similar_names, key=os.path.basename)))