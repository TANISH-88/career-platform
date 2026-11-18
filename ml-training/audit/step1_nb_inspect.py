"""Step 1 & 2 notebook inspection - read RF.ipynb data-prep cells."""
import json

nb_path = r'C:/Users/Tanish/p4/ml-training/notebooks/RF.ipynb'
with open(nb_path, encoding='utf-8') as f:
    nb = json.load(f)

print(f"Total cells: {len(nb['cells'])}")
print()

for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', []))
    if not src.strip():
        continue
    ct = cell['cell_type']
    # Print first 20 cells fully; mark augment-related
    if i <= 18:
        print(f"=== Cell {i} ({ct}) ===")
        print(src[:700])
        print()
