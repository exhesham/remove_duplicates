from os import listdir
from os.path import isfile, join
import time
import os
import hashlib
import re
import argparse
from codecs import encode, decode
parser = argparse.ArgumentParser(description='scan directory and do something with the duplicated files.')
parser.add_argument('--dir', help='A directory to scan for duplicated files', default="./", nargs=1, action='store',
                    required=True)
parser.add_argument('--recycle_bin', help='A directory used to move the duplicates', default=None, nargs=1,
                    action='store', required=False)
parser.add_argument('--list_result', help='list the duplicated files', action='store_true')
parser.add_argument('--remove_dups', help='remove duplicated files right away', action='store_true')
parser.add_argument('--save_result', help='save the founded duplicates', action='store_true')
parser.add_argument('--use_result', help='apply on the saved result only', action='store_true')
parser.add_argument('--use_cached_files_list', help='use cached files list without recursively scanning the directory',
                    action='store_true')

args = parser.parse_known_args()

files_dir = args[0].dir[0]
recycle_bin = args[0].recycle_bin[0]
move_to_recycle = False
save_result = args[0].save_result
list_result = args[0].list_result
remove_dups = args[0].remove_dups
use_cached_files_list = args[0].use_cached_files_list

FILES_IN_DIR_CACHE_NAME = 'files_to_process-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
FILES_HASHES_CACHE_NAME = 'files_hashes-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
RESULT_FILE = 'saved_result-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
OUTPUT_DIR = os.path.join(files_dir, 'output')


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
    if use_cached_files_list is True:
        cached_files = read_text_file(FILES_IN_DIR_CACHE_NAME)
        if cached_files is not None and len(cached_files) > 0:
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
            return {os.path.normpath(splitted[1]): splitted[0]}

    global imported_hashes

    print('calculating hashes...may take time...')
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

        if imported_hashes is not None and os.path.normpath(f) in imported_hashes:
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


def handle_duplicated_files(files, recycle_bin):
    for f in files:
        if remove_dups:
            os.remove(f)
        elif move_to_recycle:
            os.rename(f, os.path.join(recycle_bin, os.path.basename(f) + '.' + str(time.time())))
        if list_result:
            print("\n".join(sorted(files, key=os.path.basename)))



if __name__ == '__main__':
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    all_files = get_dir_all_files(files_dir)

    files_hash = get_files_hashes(all_files)
    get_all_hash_duplicates = get_all_duplicates_according_to_hash(files_hash)
    all_similar_names = get_all_similar_names(all_files)

    all_duplicate_files = merge_duplicates(all_similar_names, get_all_hash_duplicates)
    print('total duplicates to be deleted:', len(all_duplicate_files))
    if save_result:
        save_to_file('\n'.join(all_similar_names), RESULT_FILE)
    if remove_dups is False and list_result is False and recycle_bin is False:
        print('what do you want to do next?')
        print('1. List results')
        print('2. Move to recycle bin')
        print('3. Quit')
        while True:
            selection = input('Enter your selection:')
            if int(selection) in [1, 2, 3, 4]:
                break;
            if selection == 1:
                list_result = True
            if selection == 2:
                move_to_recycle = True
            if selection == 3:
                remove_dups = True

    handle_duplicated_files(all_duplicate_files, recycle_bin)
    # print('will delete:')


