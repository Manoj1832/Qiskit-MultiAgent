"""
Dependency graph extraction and analysis.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModuleNode:
    """Represents a module in the dependency graph."""
    name: str
    path: str
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)


class DependencyGraph:
    """
    Builds and analyzes dependency relationships in a codebase.
    """
    
    def __init__(self, repo_path: Path | str):
        """
        Initialize dependency graph builder.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self.modules: dict[str, ModuleNode] = {}
    
    def build_graph(self, package_name: str | None = None) -> None:
        """
        Build the dependency graph for Python files in the repository.
        
        Args:
            package_name: Optional package name to filter (e.g., "qiskit")
        """
        python_files = list(self.repo_path.rglob("*.py"))
        
        for file_path in python_files:
            try:
                self._process_file(file_path, package_name)
            except (SyntaxError, UnicodeDecodeError):
                continue
        
        # Build reverse dependencies
        for module_name, module in self.modules.items():
            for imported in module.imports:
                if imported in self.modules:
                    self.modules[imported].imported_by.append(module_name)
    
    def _process_file(self, file_path: Path, package_name: str | None) -> None:
        """Process a Python file to extract imports."""
        rel_path = file_path.relative_to(self.repo_path)
        module_name = str(rel_path).replace("/", ".").replace("\\", ".").rstrip(".py")
        
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if package_name and alias.name.startswith(package_name):
                        imports.append(alias.name)
                    elif not package_name:
                        imports.append(alias.name)
                        
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if package_name and node.module.startswith(package_name):
                        imports.append(node.module)
                    elif not package_name:
                        imports.append(node.module)
        
        self.modules[module_name] = ModuleNode(
            name=module_name,
            path=str(rel_path),
            imports=imports,
        )
    
    def get_dependents(self, module_name: str) -> list[str]:
        """
        Get modules that depend on the given module.
        
        Args:
            module_name: Module to find dependents for
            
        Returns:
            List of module names that import this module
        """
        if module_name in self.modules:
            return self.modules[module_name].imported_by
        return []
    
    def get_dependencies(self, module_name: str) -> list[str]:
        """
        Get modules that the given module depends on.
        
        Args:
            module_name: Module to find dependencies for
            
        Returns:
            List of module names imported by this module
        """
        if module_name in self.modules:
            return self.modules[module_name].imports
        return []
    
    def get_impact_score(self, module_name: str) -> int:
        """
        Calculate impact score based on how many modules depend on this one.
        
        Higher score means more modules would be affected by changes.
        
        Args:
            module_name: Module to calculate impact for
            
        Returns:
            Impact score (number of direct dependents)
        """
        return len(self.get_dependents(module_name))
    
    def get_affected_modules(self, module_name: str, depth: int = 2) -> set[str]:
        """
        Get all modules that could be affected by changes to a module.
        
        Args:
            module_name: Module being changed
            depth: How many levels of dependents to include
            
        Returns:
            Set of all potentially affected module names
        """
        affected = set()
        current_level = {module_name}
        
        for _ in range(depth):
            next_level = set()
            for mod in current_level:
                dependents = self.get_dependents(mod)
                for dep in dependents:
                    if dep not in affected:
                        affected.add(dep)
                        next_level.add(dep)
            current_level = next_level
        
        return affected
    
    def to_dict(self) -> dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            name: {
                "path": module.path,
                "imports": module.imports,
                "imported_by": module.imported_by,
            }
            for name, module in self.modules.items()
        }
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of the dependency graph."""
        total_edges = sum(len(m.imports) for m in self.modules.values())
        
        most_dependencies = max(
            self.modules.values(),
            key=lambda m: len(m.imports),
            default=None,
        )
        
        most_dependents = max(
            self.modules.values(),
            key=lambda m: len(m.imported_by),
            default=None,
        )
        
        return {
            "total_modules": len(self.modules),
            "total_edges": total_edges,
            "most_dependencies": most_dependencies.name if most_dependencies else None,
            "most_dependents": most_dependents.name if most_dependents else None,
        }
