import os


def list_files_in_directory(directory_path):
    all_files = os.listdir(directory_path)
    
    filenames_without_extension = [
        os.path.splitext(f)[0] for f in all_files if os.path.isfile(os.path.join(directory_path, f))
    ]    
    return all_files, filenames_without_extension
