import os
from src.cb_parser3 import CodebaseParser

# Define your custom ignore list
custom_ignore_list = [
    "__pycache__",  # Example directory to ignore
    "venv",
    "neo4j",         # Example directory to ignore
    ".git",         # Example directory to ignore
    ".DS_Store",    # Example file to ignore
    "ignore_me.py"  # Example file to ignore
]

def should_ignore(path, custom_ignore_list=['venv', '.git', '.DS_Store', '.gitignore', '__pycache__']):
    """Check if the path matches any entry in the ignore list."""
    for entry in custom_ignore_list:
        if entry in path:
            return True
    return False

def recursive_search(path, parser):
    for p in os.listdir(path):
        full_path = os.path.join(path, p)

        # Check if the path should be ignored based on the custom ignore list
        if should_ignore(full_path):
            continue

        print(full_path)

        if os.path.isfile(full_path) and p.endswith(".py"):
            print(full_path)
            parser.parse_codebase(full_path)
        elif os.path.isdir(full_path):
            # Recursively search inside the directory
            recursive_search(full_path, parser)

# Example Usage:
path = "/Users/astraeus/bitgraph"  # Update with your base path
parser = CodebaseParser("neo4j://localhost:7687", "neo4j", "mypassword")

# clear the database
parser.driver.session().run("MATCH (n) DETACH DELETE n")

# Start recursive search with custom filtering
parser.populate_codebase(path)
parser.parse_codebase(path)
