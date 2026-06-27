import re
content = open('templates/index.html', encoding='utf-8').read()
ids = sorted(set(re.findall(r'id=["\']([^"\']+)["\']', content)))
print('\n'.join(ids))
