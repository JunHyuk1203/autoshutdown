with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("${expectedExplorerPath}", "${escapeHtml(expectedExplorerPath)}")
text = text.replace("${data.path}", "${escapeHtml(data.path)}")
text = text.replace("${data.error}", "${escapeHtml(data.error)}")

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Escaped remaining innerHTML paths")
