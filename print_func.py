import ast

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

tree = ast.parse(code)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'admin_auto_update':
        start_lineno = node.lineno
        end_lineno = node.end_lineno
        lines = code.splitlines()
        print('\n'.join(lines[start_lineno-1:end_lineno]))
        break
