import json
with open('rfp_demo.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

with open('test_run.py', 'w', encoding='utf-8') as f:
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            f.write("".join(cell['source']))
            f.write("\n\n")
