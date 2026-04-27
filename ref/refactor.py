import os

def process_templates():
    with open('ref/landing_page.html', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    main_start = -1
    main_end = -1
    for i, line in enumerate(lines):
        if '<main class="flex-1">' in line:
            main_start = i
        if '</main>' in line:
            main_end = i

    base_content = "".join(lines[:main_start + 1]) + "\n        {% block content %}{% endblock %}\n    " + "".join(lines[main_end:])

    with open('frontend/templates/base.html', 'w', encoding='utf-8') as f:
        f.write(base_content)

    pages = ['landing_page.html', 'login.html', 'signup.html', 'pricing.html']
    for page in pages:
        with open('ref/' + page, 'r', encoding='utf-8') as f:
            plines = f.readlines()
        p_main_start = -1
        p_main_end = -1
        for i, l in enumerate(plines):
            if '<main' in l: p_main_start = i
            if '</main>' in l: p_main_end = i
        
        if p_main_start != -1 and p_main_end != -1:
            content = "{% extends 'base.html' %}\n{% block content %}\n" + "".join(plines[p_main_start+1:p_main_end]) + "\n{% endblock %}\n"
        else:
            content = "".join(plines)
            
        out_name = page
        if out_name == 'landing_page.html': out_name = 'index.html'
        
        with open('frontend/templates/frontend/' + out_name, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == '__main__':
    process_templates()
