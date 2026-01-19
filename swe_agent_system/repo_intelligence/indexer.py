"""
Repository indexer for codebase understanding.
"""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FileInfo:
    """Information about a file in the repository."""
    path: str
    size: int
    extension: str
    is_python: bool
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass
class RepositoryIndex:
    """Index of a repository's structure and contents."""
    root_path: str
    total_files: int
    python_files: int
    files: dict[str, FileInfo] = field(default_factory=dict)
    class_map: dict[str, str] = field(default_factory=dict)  # class_name -> file_path
    function_map: dict[str, str] = field(default_factory=dict)  # func_name -> file_path


class RepositoryIndexer:
    """
    Indexes a repository for quick lookup and targeted context retrieval.
    """
    
    def __init__(self, repo_path: Path | str):
        """
        Initialize repository indexer.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self.index: RepositoryIndex | None = None
        
        # Default ignore patterns
        self.ignore_patterns = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".egg-info",
            "dist",
            "build",
            ".tox",
        }
    
    def build_index(self) -> RepositoryIndex:
        """
        Build an index of the repository.
        
        Returns:
            RepositoryIndex with file and symbol mappings
        """
        self.index = RepositoryIndex(
            root_path=str(self.repo_path),
            total_files=0,
            python_files=0,
        )
        
        for root, dirs, files in os.walk(self.repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(self.repo_path))
                
                self.index.total_files += 1
                
                if file.endswith(".py"):
                    self.index.python_files += 1
                    file_info = self._analyze_python_file(file_path, rel_path)
                else:
                    file_info = FileInfo(
                        path=rel_path,
                        size=file_path.stat().st_size,
                        extension=file_path.suffix,
                        is_python=False,
                    )
                
                self.index.files[rel_path] = file_info
        
        return self.index
    
    def _analyze_python_file(self, file_path: Path, rel_path: str) -> FileInfo:
        """Analyze a Python file to extract structure."""
        file_info = FileInfo(
            path=rel_path,
            size=file_path.stat().st_size,
            extension=".py",
            is_python=True,
        )
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    file_info.classes.append(node.name)
                    if self.index:
                        self.index.class_map[node.name] = rel_path
                        
                elif isinstance(node, ast.FunctionDef):
                    # Only top-level functions
                    if isinstance(node, ast.FunctionDef):
                        file_info.functions.append(node.name)
                        if self.index:
                            self.index.function_map[node.name] = rel_path
                            
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        file_info.imports.append(alias.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_info.imports.append(node.module)
                        
        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            pass
        
        return file_info
    
    def find_files_by_class(self, class_name: str) -> list[str]:
        """Find files containing a specific class."""
        if not self.index:
            self.build_index()
        
        assert self.index is not None
        
        if class_name in self.index.class_map:
            return [self.index.class_map[class_name]]
        
        # Fuzzy search
        matches = []
        for name, path in self.index.class_map.items():
            if class_name.lower() in name.lower():
                matches.append(path)
        return matches
    
    def find_files_by_function(self, function_name: str) -> list[str]:
        """Find files containing a specific function."""
        if not self.index:
            self.build_index()
        
        assert self.index is not None
        
        if function_name in self.index.function_map:
            return [self.index.function_map[function_name]]
        
        # Fuzzy search
        matches = []
        for name, path in self.index.function_map.items():
            if function_name.lower() in name.lower():
                matches.append(path)
        return matches
    
    def find_files_by_import(self, module_name: str) -> list[str]:
        """Find files that import a specific module."""
        if not self.index:
            self.build_index()
        
        assert self.index is not None
        
        matches = []
        for path, info in self.index.files.items():
            if info.is_python:
                for imp in info.imports:
                    if module_name in imp:
                        matches.append(path)
                        break
        return matches
    
    def get_file_context(self, file_path: str, max_lines: int = 500) -> str:
        """
        Get the content of a file for context injection.
        
        Args:
            file_path: Relative path to the file
            max_lines: Maximum lines to return
            
        Returns:
            File content (possibly truncated)
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return ""
        
        try:
            lines = full_path.read_text(encoding="utf-8").split("\n")
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n... (truncated, {len(lines) - max_lines} more lines)"
            return "\n".join(lines)
        except UnicodeDecodeError:
            return "[Binary or non-UTF8 file]"
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the repository index."""
        if not self.index:
            self.build_index()
        
        assert self.index is not None
        
        return {
            "root_path": self.index.root_path,
            "total_files": self.index.total_files,
            "python_files": self.index.python_files,
            "total_classes": len(self.index.class_map),
            "total_functions": len(self.index.function_map),
        }
