import re
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

js_bindings = "\nwindow.addEventListener('DOMContentLoaded', () => {\n"

def process_line(line):
    global js_bindings
    # skip lines with template literals which we handle with event delegation
    if "${" in line:
        return line
        
    def repl(match):
        global js_bindings
        full_tag = match.group(0)
        
        # Check if it has an id
        id_match = re.search(r'id="([^"]+)"', full_tag)
        if id_match:
            el_id = id_match.group(1)
            new_tag = full_tag
        else:
            el_id = "auto_id_" + str(uuid.uuid4())[:8]
            # insert id right after the tag name
            tag_name_match = re.match(r'<([a-zA-Z0-9_-]+)', full_tag)
            if tag_name_match:
                tag_name = tag_name_match.group(1)
                new_tag = full_tag.replace(f'<{tag_name}', f'<{tag_name} id="{el_id}"', 1)
            else:
                new_tag = full_tag
        
        # extract all onX handlers
        handlers = re.findall(r'(on[a-z]+)="([^"]+)"', new_tag)
        for evt, code in handlers:
            # remove the inline handler
            new_tag = new_tag.replace(f'{evt}="{code}"', "")
            
            # handle special cases like "if(event.target===this)closeAdminPanel()"
            if "event.target===this" in code:
                code = code.replace("event.target===this", "e.target===this").replace("closeAdminPanel()", "closeAdminPanel();")
            elif "event.stopPropagation()" in code:
                code = code.replace("event.stopPropagation()", "e.stopPropagation();")
                
            js_bindings += f"    const el_{el_id.replace('-', '_')} = document.getElementById('{el_id}');\n"
            js_bindings += f"    if (el_{el_id.replace('-', '_')}) el_{el_id.replace('-', '_')}.addEventListener('{evt[2:]}', (e) => {{ {code} }});\n"
            
        return new_tag
        
    # Replace anything that looks like an HTML tag with inline handlers
    return re.sub(r'<[^>]+on[a-z]+="[^"]+"[^>]*>', repl, line)

new_lines = []
for line in lines:
    new_lines.append(process_line(line))

js_bindings += "});\n"

text = "".join(new_lines)

# Handle the template literal ones by adding them to the delegation script
# We already did some of them, let's just make sure we didn't leave any.
text = text.replace('onclick="renderScheduleTabs(\'${day}\')"', 'data-action="renderScheduleTabs" data-day="${day}"')
text = text.replace('onclick="selectExplorerItem(\'${safeName}\', ${isFolder})"', 'data-action="selectExplorerItem" data-name="${safeName}" data-isfolder="${isFolder}"')
text = text.replace('onclick="approveUser(\'${escapeHtml(uid)}\',\'${safeEmail.replace(/\\'/g, \\"\\\\\'\\")}\')"', 'data-action="approveUser" data-uid="${escapeHtml(uid)}" data-email="${safeEmail.replace(/\\'/g, \\"\\\\\'\\")}"')
text = text.replace('onclick="rejectUser(\'${escapeHtml(uid)}\',\'${safeEmail.replace(/\\'/g, \\"\\\\\'\\")}\')"', 'data-action="rejectUser" data-uid="${escapeHtml(uid)}" data-email="${safeEmail.replace(/\\'/g, \\"\\\\\'\\")}"')


text = text.replace('</script>\n</body>', js_bindings + '</script>\n</body>')

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Done processing inline handlers via regex.")
