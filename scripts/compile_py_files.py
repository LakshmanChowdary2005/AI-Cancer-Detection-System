"""Compile all .py files in the repository (useful helper).

Avoids accidentally running `py_compile` on non-Python files (HTML, etc.).

Usage:
    python scripts/compile_py_files.py
"""
import os
import py_compile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
for dirpath, dirnames, filenames in os.walk(root):
    # skip venv and hidden folders
    if '.venv' in dirpath or 'venv' in dirpath or dirpath.startswith('.'):
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        try:
            py_compile.compile(path, doraise=True)
            print('OK:', os.path.relpath(path, root))
        except Exception as e:
            errors.append((path, str(e)))

if errors:
    print('\nFound compile errors:')
    for p, msg in errors:
        print(p, msg)
    raise SystemExit(1)
else:
    print('\nAll Python files compiled successfully.')
