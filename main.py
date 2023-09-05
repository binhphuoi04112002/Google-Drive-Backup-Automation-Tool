import shutil

# specify the directory to be backed up and the backup location
dir_to_backup = '/path/to/dir'
backup_location = '/path/to/backup/location'

# copy the directory to the backup location
shutil.copytree(dir_to_backup, backup_location)
