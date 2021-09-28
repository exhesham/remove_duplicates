import json
from os import listdir
import mimetypes
import time
import os
import hashlib
import re
import argparse
import eyed3

mimetypes.init()

parser = argparse.ArgumentParser(description='scan directory and do something with the duplicated files.')

parser.add_argument('--dir', help='A directory to scan for duplicated files', default="./", nargs=1, action='store', required=True)
parser.add_argument('--operation', help='recycle/delete/none', default='none', nargs=1, action='store', choices=['recycle', 'delete', 'none'], required=True)
parser.add_argument('--recycle_bin', help='A directory used to move the duplicates', default=None, nargs=1, action='store', required=False)
parser.add_argument('--list_result', help='list the duplicated files', action='store_true')
parser.add_argument('--consider_all', help='consider all possible criterions when checking for duplicates: identical basename/ artist - title/file hash', action='store_true')
parser.add_argument('--consider_same_hash', help='consider duplicates with same hash', action='store_true')
parser.add_argument('--consider_same_name', help='consider duplicates with same filename', action='store_true')
parser.add_argument('--consider_same_artist_title', help='consider duplicates with same artist - title', action='store_true')
parser.add_argument('--use_cached_files_list', help='use cached files list without recursively scanning the directory', action='store_true')

args = parser.parse_known_args()

files_dir = args[0].dir[0]
recycle_bin = args[0].recycle_bin[0] if args[0].recycle_bin is not None else None
list_result = args[0].list_result
operation = args[0].operation[0]
consider_all = True if not args[0].consider_same_hash and not args[0].consider_same_name and not args[0].consider_same_artist_title else False
consider_same_hash = args[0].consider_same_hash
consider_same_name = args[0].consider_same_name
consider_same_artist_title = args[0].consider_same_artist_title
use_cached_files_list = args[0].use_cached_files_list

FILES_IN_DIR_CACHE_NAME = 'files_to_process-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
FILES_HASHES_CACHE_NAME = 'files_hashes-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
MP3_EYE3D_FAILS_RESULT_FILE = 'eye3d_fails-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
MP3_METADATA_DUMP = 'eye3d_dump-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
RESULT_FILE = 'saved_result-%s.txt' % hashlib.sha256(files_dir.encode('utf-8')).hexdigest()
OUTPUT_DIR = os.path.join(files_dir, 'output')

def is_music_file(filepath):
    mimestart = mimetypes.guess_type(filepath)[0]
    if mimestart != None:
        mimestart = mimestart.split('/')[0]
        if mimestart == 'audio':
            return True
    else:
        return None
    return False

##############################################################################
## text files operations
##############################################################################

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
    # save list to file
    with open(os.path.join(OUTPUT_DIR, filename), 'a', encoding="utf-8") as f:
        f.write(line + '\n')


def save_to_file(text, filename):
    # save list to file
    with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding="utf-8") as f:
        f.write(text)

##############################################################################
## app helpers
##############################################################################

def scan_dir(path):
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

    save_to_file('\n'.join(str(e) for e in files), FILES_IN_DIR_CACHE_NAME)
    return files


##############################################################################
## app duplicate logic helpers
##############################################################################

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
            return [os.path.normpath(splitted[1]), splitted[0]]

    global imported_hashes

    if imported_hashes is None:
        text = read_text_file(FILES_HASHES_CACHE_NAME)
        if text is not None and len(text) > 0:
            imported_hashes = {hash_formatter(v)[0]: hash_formatter(v)[1] for v in text}
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


def choose_best_name(names):
    def copy_indication_is_absent(name):
        x = re.search("\(\d*\)", name)
        if x:
            return False
        if '- copy' in name.lower():
            return False
        return True

    result = list(filter(lambda x: copy_indication_is_absent(x), names))
    if len(result) == 0:
        # print("found zero on", names)
        return names[0]
    return result[0]


def get_all_duplicates_according_to_hash(hashes):
    all_dups = []
    for h in hashes:
        if len(hashes[h]) > 1:
            chosen_file = choose_best_name(hashes[h])
            for name in hashes[h]:
                if name != chosen_file and name.endswith(".mp3"):
                    all_dups.append(name)
    return all_dups


def get_files_artist_title_metadata(files):
    hashes = {}
    failed = []
    for f in files:

        if is_music_file(f) is False:
            continue

        try:
            audio_netadata = eyed3.load(f)
            if audio_netadata.tag.artist is None or audio_netadata.tag.title is None:
                failed.append(f)
                continue
            file_hash = '%s - %s' % (audio_netadata.tag.artist, audio_netadata.tag.title)
            hashes.setdefault(file_hash, []).append(f)
        except:
            failed.append(f)
    if len(failed) > 0:
        print('failed to find metadata for ', len(failed), ' files. See the file ', MP3_EYE3D_FAILS_RESULT_FILE,
              ' for more info')
        save_to_file('\n'.join(failed), MP3_EYE3D_FAILS_RESULT_FILE)
    return hashes


def get_mp3_metadata_duplicates(eye3d_dups_map):
    all_dups = []
    for d in eye3d_dups_map:
        if len(eye3d_dups_map[d]) > 0:
            chosen_file = choose_best_name(eye3d_dups_map[d])
            for name in eye3d_dups_map[d]:
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


##############################################################################
## app result helpers
##############################################################################

def merge_duplicates(dupsnames, hashes, mp3dups):
    hashes_files = []
    if consider_all or consider_same_name:
        hashes_files.extend(dupsnames)
    if consider_all or consider_same_hash:
        hashes_files.extend(hashes)
    if consider_all or consider_same_artist_title:
        hashes_files.extend(mp3dups)
    return list(dict.fromkeys(hashes_files))


def handle_duplicated_files(files):
    for f in files:
        if operation == 'delete':
            os.remove(f)
        elif operation == 'recycle':
            os.rename(f, os.path.join(recycle_bin, os.path.basename(f) + '.' + str(time.time())))


def create_report(all_files, duplicates, mp3_hashes, crypto_hashes, duplicate_names):
    def find_in_hash(value, dictionary):
        for key, value in dictionary.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
            if f in value:
                return key
        return None

    report = []
    for f in all_files:
        file_report = {
            "file_name": os.path.basename(f),
            "file_path": f,
            "hash": find_in_hash(f, crypto_hashes),
            "title": find_in_hash(f, mp3_hashes),
            "has_brother_same_name": f in duplicate_names,
            "is_duplicate": f in duplicates
        }
        report.append(file_report)
    return report

##############################################################################
## Main
##############################################################################

if __name__ == '__main__':
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    print('* scanning dirctory %s...' % files_dir)
    all_files = scan_dir(files_dir)
    print('√ found ', len(all_files), 'files')

    hash_dups = []
    if consider_all or consider_same_hash:
        print('* calculating hashes...')
        hash_to_files_map = get_files_hashes(all_files)
        hash_dups = get_all_duplicates_according_to_hash(hash_to_files_map)
        print('√ found ', len(hash_dups), ' hash duplicates')

    identical_names = []
    if consider_all or consider_same_name:
        print('* finding duplicate names...')
        identical_names = get_all_similar_names(all_files)
        print('√ found ', len(identical_names), ' identical names duplicates')

    mp3_metadata_duplicates = []
    if consider_all or consider_same_artist_title:
        print('* finding audio metadata...')
        mp3_metadata_to_files_map = get_files_artist_title_metadata(all_files)
        save_to_file(json.dumps(mp3_metadata_to_files_map), MP3_METADATA_DUMP)
        mp3_metadata_duplicates = get_mp3_metadata_duplicates(mp3_metadata_to_files_map)
        print('√ found ', len(mp3_metadata_duplicates), ' metadata duplicates')

    all_duplicate_files = merge_duplicates(identical_names, hash_dups, mp3_metadata_duplicates)
    print('---------------------------------------------------------------')
    print('√ total duplicates found:', len(all_duplicate_files))
    print('Note: The selected operation to apply on the duplicated files is:', operation)
    print('---------------------------------------------------------------')
    if list_result:
        print('the duplicated files are:' if len(all_duplicate_files) > 0 else 'No duplicates :)')
        print("\n".join(sorted(all_duplicate_files, key=os.path.basename)))
    # (all_files, duplicates,mp3_hashes,crypto_hashes, duplicate_names
    save_to_file(json.dumps(
        create_report(all_files=all_files, duplicates=all_duplicate_files, mp3_hashes=mp3_metadata_to_files_map,
                      crypto_hashes=hash_to_files_map, duplicate_names=identical_names)), RESULT_FILE)
    # if remove_all_dups is False and list_result is False and recycle_bin is False:
    #     print('what do you want to do next?')
    #     print('1. List results')
    #     print('2. Move to recycle bin')
    #     print('3. Delete')
    #     print('4. Quit')
    #     while True:
    #         selection = input('Enter your selection:')
    #         if int(selection) in [1, 2, 3, 4]:
    #             break
    #         if selection == 4:
    #             break
    #         if selection == 1:
    #             list_result = True
    #         if selection == 2:
    #             move_to_recycle = True
    #         if selection == 3:
    #             remove_all_dups = True

    handle_duplicated_files(all_duplicate_files)
    # print('will delete:')
