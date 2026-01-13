import os
import shutil

#clean all files and folders in static/dist
dist_folder = "static/dist"
shutil.rmtree(dist_folder, ignore_errors=True)
print(f'Cleaned {dist_folder} folder.')
os.makedirs(dist_folder, exist_ok=True)