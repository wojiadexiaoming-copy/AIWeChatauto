content = open('app_new.py', encoding='utf-8').read()
old = "return render_template('index.html')"
new = "return render_template('base.html')"
if old in content:
    open('app_new.py', 'w', encoding='utf-8').write(content.replace(old, new, 1))
    print('OK')
else:
    print('NOT FOUND')
