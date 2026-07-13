import os

files = [
    "dashboard/src/app/dashboard/jurisdictions/page.tsx",
    "dashboard/src/app/dashboard/jurisdictions/[id]/page.tsx",
    "dashboard/src/app/dashboard/jurisdictions/create/page.tsx",
    "dashboard/src/app/dashboard/compliance/page.tsx"
]

replacements = [
    ("bg-white dark:bg-slate-100 dark:bg-slate-900", "bg-white dark:bg-slate-900"),
    ("bg-slate-100 dark:bg-slate-200 dark:bg-slate-800/50", "bg-slate-100 dark:bg-slate-800/50"),
    ("dark:bg-slate-100 dark:bg-slate-900", "dark:bg-slate-900"),
    ("dark:bg-slate-100 dark:bg-slate-800", "dark:bg-slate-800")
]

for filepath in files:
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, "r") as f:
        content = f.read()
        
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, "w") as f:
        f.write(content)
