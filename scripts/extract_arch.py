import os
import json
import re

arch_dir = 'docs/architecture'
elements = {}

for root, dirs, files in os.walk(arch_dir):
    for file in files:
        if file.endswith('.md'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
                # Just extract headings for now to see what we're dealing with
                headings = re.findall(r'^(#{1,4})\s+(.+)$', content, re.MULTILINE)
                elements[filepath] = [h[1] for h in headings]

with open('scripts/arch_summary.json', 'w') as f:
    json.dump(elements, f, indent=2)

print("Extraction complete. Found", len(elements), "documents.")
