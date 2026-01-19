"""Tests for repository intelligence modules."""

import pytest
import tempfile
from pathlib import Path
from swe_agent_system.repo_intelligence.indexer import (
    RepositoryIndexer,
    RepositoryIndex,
    FileInfo,
)
from swe_agent_system.repo_intelligence.dependency_graph import (
    DependencyGraph,
    ModuleNode,
)


class TestFileInfo:
    """Tests for FileInfo dataclass."""
    
    def test_file_info_creation(self):
        """Should create FileInfo with all fields."""
        info = FileInfo(
            path="test/module.py",
            size=1024,
            extension=".py",
            is_python=True,
            classes=["MyClass"],
            functions=["my_function"],
            imports=["os", "sys"],
        )
        
        assert info.path == "test/module.py"
        assert info.size == 1024
        assert info.is_python
        assert "MyClass" in info.classes
        assert "my_function" in info.functions


class TestRepositoryIndexer:
    """Tests for RepositoryIndexer class."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            
            # Create Python files
            (repo / "module.py").write_text("""
import os
from typing import Any

class MyClass:
    def method(self):
        pass

def standalone_function():
    pass
""")
            
            (repo / "subdir").mkdir()
            (repo / "subdir" / "submodule.py").write_text("""
from module import MyClass

def helper():
    pass
""")
            
            yield repo
    
    def test_build_index(self, temp_repo):
        """Should build index of repository files."""
        indexer = RepositoryIndexer(temp_repo)
        index = indexer.build_index()
        
        assert index.total_files >= 2
        assert index.python_files >= 2
    
    def test_find_files_by_class(self, temp_repo):
        """Should find files containing a class."""
        indexer = RepositoryIndexer(temp_repo)
        indexer.build_index()
        
        files = indexer.find_files_by_class("MyClass")
        assert len(files) >= 1
        assert any("module.py" in f for f in files)
    
    def test_find_files_by_function(self, temp_repo):
        """Should find files containing a function."""
        indexer = RepositoryIndexer(temp_repo)
        indexer.build_index()
        
        files = indexer.find_files_by_function("standalone_function")
        assert len(files) >= 1
    
    def test_get_file_context(self, temp_repo):
        """Should get file content."""
        indexer = RepositoryIndexer(temp_repo)
        
        content = indexer.get_file_context("module.py")
        assert "MyClass" in content
        assert "standalone_function" in content
    
    def test_get_summary(self, temp_repo):
        """Should return summary statistics."""
        indexer = RepositoryIndexer(temp_repo)
        indexer.build_index()
        
        summary = indexer.get_summary()
        assert "total_files" in summary
        assert "python_files" in summary
        assert "total_classes" in summary
        assert "total_functions" in summary


class TestDependencyGraph:
    """Tests for DependencyGraph class."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            
            (repo / "mypackage").mkdir()
            (repo / "mypackage" / "__init__.py").write_text("")
            
            (repo / "mypackage" / "core.py").write_text("""
import os
""")
            
            (repo / "mypackage" / "utils.py").write_text("""
from mypackage.core import something
""")
            
            (repo / "mypackage" / "main.py").write_text("""
from mypackage.core import other
from mypackage.utils import helper
""")
            
            yield repo
    
    def test_build_graph(self, temp_repo):
        """Should build dependency graph."""
        graph = DependencyGraph(temp_repo)
        graph.build_graph("mypackage")
        
        assert len(graph.modules) >= 3
    
    def test_get_dependencies(self, temp_repo):
        """Should return module dependencies."""
        graph = DependencyGraph(temp_repo)
        graph.build_graph("mypackage")
        
        # utils depends on core
        for name, module in graph.modules.items():
            if "utils" in name:
                assert any("core" in dep for dep in module.imports)
    
    def test_get_summary(self, temp_repo):
        """Should return graph summary."""
        graph = DependencyGraph(temp_repo)
        graph.build_graph()
        
        summary = graph.get_summary()
        assert "total_modules" in summary
        assert "total_edges" in summary
