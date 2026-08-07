import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)

with open("test.html", "w", encoding="utf-8") as f:
    f.write("<html><body><script>")
    f.write("window.onerror = function(msg, url, lineNo, columnNo, error) { console.log('ERROR: ' + msg + ' at line ' + lineNo); return false; };\n")
    for s in scripts:
        f.write(s)
    f.write("</script></body></html>")
