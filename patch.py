import re

with open('auto_shutdown.py', 'r', encoding='utf-8') as f:
    content = f.read()

def patch_block(match):
    original = match.group(0)
    lines = original.split('\n')
    
    # Check if already patched
    if 'commands_to_process' in original:
        return original
        
    out = []
    
    # 1. Modify the header part
    out.append('                if cmd and isinstance(cmd, dict):')
    out.append('                    commands_to_process = []')
    out.append('                    if "action" in cmd:')
    out.append('                        commands_to_process.append((None, cmd))')
    out.append('                    else:')
    out.append('                        for push_id, payload in cmd.items():')
    out.append('                            if isinstance(payload, dict) and "action" in payload:')
    out.append('                                commands_to_process.append((push_id, payload))')
    out.append('')
    out.append('                    for push_id, payload in commands_to_process:')
    out.append('                        action = payload.get("action")')
    out.append('                        message = payload.get("message", "")')
    
    header_end = False
    for line in lines:
        if not header_end:
            if 'message = cmd.get("message", "")' in line:
                header_end = True
            continue
            
        # Add 4 spaces to the remaining lines
        if line.strip():
            if 'del_url = f"{central_url.rstrip(' + "'" + '/' + "'" + ')}/commands/{pc_id}.json"' in line:
                out.append('                            if push_id:')
                out.append('                                del_url = f"{central_url.rstrip(' + "'" + '/' + "'" + ')}/commands/{pc_id}/{push_id}.json"')
                out.append('                            else:')
                out.append('                                ' + line)
            else:
                out.append('    ' + line)
        else:
            out.append(line)
            
    return '\n'.join(out)

# Pattern for threads
pattern = r'                if cmd and isinstance\(cmd, dict\):\n                    action = cmd\.get\(\"action\"\)\n                    message = cmd\.get\(\"message\", \"\"\)\n.*?(?=            except Exception as ge:)'

content = re.sub(pattern, patch_block, content, flags=re.DOTALL)

with open('auto_shutdown.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patch complete.')
