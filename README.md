# Spot duplicated audio files

The goal of this app is to find duplicated music files and do something about them.

The files are spotted according to:
1. Identical file name
2. Identical file hash
3. Identical track artist and title.

you can decide either to use all of these criterions or to use a specific one by choosing the right flag.

## Setup

You need python 3.x to run this app.

1. install python 3.x
2. install pip
```
pip install eyed3 
```

## Arguments:

Run the script with `-h` to find out what arguments are available...

## Examples

### Delete all duplicates by name, hash and artist-title example
```
python music_duplicates.py --dir "C:\Users\Hesham\Music\atb" --save_result --operation=delete
```

### Recycle all duplicates by hash and artist-title only
```
python music_duplicates.py --dir "C:\Users\Hesham\Music\atb" --recycle_bin "D:\dups" --save_result --operation=recycle --consider_same_hash --consider_same_artist_title 
```

### Find duplicated and do list them only
```
python music_duplicates.py --dir "C:\Users\Hesham\Music\atb" --list_result --save_result --operation=none
```