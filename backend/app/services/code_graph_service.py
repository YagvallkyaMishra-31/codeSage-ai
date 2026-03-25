"""
Code Graph Service: parses codebase to understand relationships.
Extracts imports, function definitions, and function calls using Regex.
"""
import os
import re
from pathlib import Path


def extract_js_ts_info(content: str) -> dict:
    """Extract graph info from JS/TS code."""
    # 1. Imports
    imports = []
    # match: import { foo } from './bar' OR import foo from 'bar'
    import_matches = re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
    for m in import_matches:
        imports.append(m.group(1))

    # match: const foo = require('./bar')
    require_matches = re.finditer(r'require\([\'"]([^\'"]+)[\'"]\)', content)
    for m in require_matches:
        imports.append(m.group(1))

    # 2. Functions
    functions = []
    # match: function foo()
    fn_matches = re.finditer(r'function\s+([a-zA-Z_$][0-9a-zA-Z_$]*)\s*\(', content)
    for m in fn_matches:
        functions.append(m.group(1))

    # match: const foo = () => OR const foo = function()
    arrow_matches = re.finditer(r'(?:const|let|var)\s+([a-zA-Z_$][0-9a-zA-Z_$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z_$][0-9a-zA-Z_$]*)\s*=>', content)
    for m in arrow_matches:
        functions.append(m.group(1))

    # 3. Calls
    calls = []
    # match: foo() or obj.foo()
    call_matches = re.finditer(r'([a-zA-Z_$][0-9a-zA-Z_$]*)\s*\(', content)
    for m in call_matches:
        call_name = m.group(1)
        # Filter out common keywords
        if call_name not in ['if', 'for', 'while', 'switch', 'catch', 'function', 'return']:
            calls.append(call_name)

    return {
        "imports": list(set(imports)),
        "functions": list(set(functions)),
        "calls": list(set(calls))
    }


def extract_python_info(content: str) -> dict:
    """Extract graph info from Python code."""
    imports = []
    # match: import foo, bar OR from foo import bar
    import_matches = re.finditer(r'^(?:from\s+([^\s]+)\s+)?import\s+(.*?)$', content, re.MULTILINE)
    for m in import_matches:
        if m.group(1):
            imports.append(m.group(1))
        # Add the imported modules
        for mod in m.group(2).split(','):
            imports.append(mod.strip().split(' ')[0]) # handle 'import foo as bar'

    functions = []
    # match: def foo():
    fn_matches = re.finditer(r'def\s+([a-zA-Z_][0-9a-zA-Z_]*)\s*\(', content)
    for m in fn_matches:
        functions.append(m.group(1))

    calls = []
    # match: foo() or obj.foo()
    call_matches = re.finditer(r'([a-zA-Z_][0-9a-zA-Z_]*)\s*\(', content)
    for m in call_matches:
        call_name = m.group(1)
        if call_name not in ['if', 'while', 'for', 'def', 'class', 'elif', 'return']:
            calls.append(call_name)

    return {
        "imports": list(set(imports)),
        "functions": list(set(functions)),
        "calls": list(set(calls))
    }


def build_code_graph(local_path: str) -> dict:
    """
    Build a dependency graph for an entire repository.
    Returns: { "relative/path/file.js": { "imports": [], "functions": [], "calls": [] } }
    """
    graph = {}
    base_dir = Path(local_path)

    for root, dirs, files in os.walk(local_path):
        # Skip hidden dirs, node_modules, inside venv etc
        dirs_to_remove = [d for d in dirs if d.startswith('.') or d in ['node_modules', 'venv', '__pycache__', 'dist', 'build']]
        for d in dirs_to_remove:
            dirs.remove(d)

        for file in files:
            file_path = Path(root) / file
            
            # Use forward slashes for cross-platform relative paths
            try:
                rel_path = file_path.relative_to(base_dir).as_posix()
            except ValueError:
                rel_path = str(file_path).replace('\\', '/')

            ext = file_path.suffix.lower()

            try:
                if ext in ['.js', '.jsx', '.ts', '.tsx']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        graph[rel_path] = extract_js_ts_info(f.read())
                elif ext in ['.py']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        graph[rel_path] = extract_python_info(f.read())
            except Exception:
                continue

    return graph
