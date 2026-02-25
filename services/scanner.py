import os
from typing import Set, Generator

class ImageScanner:
    """Handles filesystem scanning to detect image files."""

    def __init__(self, allowed_extensions: Set[str]):
        self.allowed_extensions = {ext.lower().strip() for ext in allowed_extensions}
    
    def walk_images(self, root_path: str, recursive: bool) -> Generator[str, None, None]:
        if not self.is_valid_directory(root_path):
            return
        
        walker = self._walk_recursive if recursive else self.walk_non_recursive
        yield from walker(root_path, self._is_image)
    

    def _walk_recursive(self, root_path: str, is_image) -> Generator[str, None, None]:
        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                if is_image(filename):
                    yield os.path.abspath(os.path.join(dirpath, filename))

    def walk_non_recursive(self, root_path: str, is_image) -> Generator[str, None, None]:
        try:
            with os.scandir(root_path) as entries:
                for entry in entries:
                    if entry.is_file() and is_image(entry.name):
                        yield os.path.abspath(entry.path)
        except PermissionError:
            return
    
    def is_valid_directory(self, path: str) -> bool:
        return os.path.isdir(path)
    
    def _is_image(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.allowed_extensions