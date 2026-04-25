from langchain_core.tools import tool
import os

@tool
def read_file(filepath: str) -> str:
    """Read a text file and return its contents.
    Use this to read any file on the filesystem by providing its path."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: file not found: {filepath}"
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(filepath: str, content: str) -> str:
    """Write content to a file, creating it and any necessary directories."""
    try:
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"