"""
Basic file management
@jarviscmd: Move, copy, or delete a file.
"""

import shutil, os

def run():
    print("1. Move\n2. Copy\n3. Delete")
    choice = input("Select: ")
    path = input("File path: ")
    if choice == "1":
        dest = input("Destination: ")
        shutil.move(path, dest)
        print(f"Moved to {dest}")
    elif choice == "2":
        dest = input("Destination: ")
        shutil.copy2(path, dest)
        print(f"Copied to {dest}")
    elif choice == "3":
        os.remove(path)
        print(f"Deleted {path}")
    else:
        print("Invalid choice.")
