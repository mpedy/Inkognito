import os

#clean all files and folders in static/dist
dist_folder = "static/dist"
for filename in os.listdir(dist_folder):
    file_path = os.path.join(dist_folder, filename)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            import shutil
            shutil.rmtree(file_path)
    except Exception as e:
        print(f'Failed to delete {file_path}. Reason: {e}')
print(f'Cleaned {dist_folder} folder.')