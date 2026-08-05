import base64
import marshal
import zlib

with open('auto_shutdown.py', 'r', encoding='utf-8') as f:
    code_text = f.read()

# Extract all imports
imports = []
for line in code_text.split('\n'):
    line = line.strip()
    # We only care about top-level imports that don't depend on local logic, 
    # but to be safe we'll just grab all standard looking ones that don't have indentation.
    if line.startswith('import ') or line.startswith('from '):
        imports.append(line)

compiled = compile(code_text, '<auto_shutdown>', 'exec')
marshalled = marshal.dumps(compiled)
compressed = zlib.compress(marshalled)
encoded = base64.b64encode(compressed).decode('utf-8')

# We inject the original imports so PyInstaller's AST parser detects them!
runner_code = '\n'.join(imports) + '\n\n'
runner_code += "import marshal, zlib, base64\n"
runner_code += f"encoded_payload = '{encoded}'\n"
runner_code += "exec(marshal.loads(zlib.decompress(base64.b64decode(encoded_payload))), globals())\n"

with open('auto_shutdown_runner.py', 'w', encoding='utf-8') as f:
    f.write(runner_code)

print("Created auto_shutdown_runner.py")
