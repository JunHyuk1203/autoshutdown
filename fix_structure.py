with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find if __name__ == "__main__":
main_idx = -1
for i, line in enumerate(lines):
    if line.startswith('if __name__ == "__main__":'):
        main_idx = i
        break

if main_idx != -1:
    # Lines from main_idx+2 to where `import os` starts (which is the swallowed main logic)
    # We need to find `    import os` which is after `disable_auto_logon`
    import_os_idx = -1
    for i in range(main_idx+2, len(lines)):
        if lines[i].startswith('    import os'):
            import_os_idx = i
            break
    
    if import_os_idx != -1:
        # Extract the functions
        funcs_code = lines[main_idx+2 : import_os_idx]
        
        # Remove them from the bottom
        del lines[main_idx+2 : import_os_idx]
        
        # Insert them at the top (after import sys at line 2)
        lines = lines[:2] + funcs_code + lines[2:]
        
        with open("auto_shutdown.py", "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("Fixed structure!")
    else:
        print("Could not find import os")
else:
    print("Could not find main block")
