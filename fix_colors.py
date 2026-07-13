import os

files = [
    "dashboard/src/app/dashboard/jurisdictions/page.tsx",
    "dashboard/src/app/dashboard/jurisdictions/[id]/page.tsx",
    "dashboard/src/app/dashboard/jurisdictions/create/page.tsx",
    "dashboard/src/app/dashboard/compliance/page.tsx"
]

replacements = [
    ("bg-[#0f172a]", "bg-slate-50 dark:bg-slate-950"),
    ("bg-[#0b1120]", "bg-white dark:bg-slate-900"),
    ("text-slate-300", "text-slate-700 dark:text-slate-300"),
    ("text-slate-400", "text-slate-600 dark:text-slate-400"),
    ("text-slate-200", "text-slate-800 dark:text-slate-200"),
    ("border-slate-800", "border-slate-200 dark:border-slate-800"),
    ("border-slate-700", "border-slate-300 dark:border-slate-700"),
    ("bg-slate-900", "bg-slate-100 dark:bg-slate-900"),
    ("bg-slate-800/50", "bg-slate-100 dark:bg-slate-800/50"),
    ("bg-slate-800", "bg-slate-200 dark:bg-slate-800"),
    ("hover:bg-slate-800/30", "hover:bg-slate-100 dark:hover:bg-slate-800/30"),
    ("hover:bg-slate-800/20", "hover:bg-slate-100 dark:hover:bg-slate-800/20"),
    ("bg-slate-900/50", "bg-slate-50 dark:bg-slate-900/50"),
    ("text-white", "text-slate-900 dark:text-white"),
]

# Fix buttons that use text-white
button_fixes = [
    ("bg-blue-600 hover:bg-blue-500 text-slate-900 dark:text-white", "bg-blue-600 hover:bg-blue-500 text-white"),
    ("bg-emerald-600 hover:bg-emerald-500 text-slate-900 dark:text-white", "bg-emerald-600 hover:bg-emerald-500 text-white"),
    ("bg-emerald-500 text-slate-900 dark:text-white", "bg-emerald-500 text-white"),
    ("bg-blue-600 text-slate-900 dark:text-white", "bg-blue-600 text-white")
]

for filepath in files:
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}")
        continue
    
    with open(filepath, "r") as f:
        content = f.read()
        
    for old, new in replacements:
        content = content.replace(old, new)
        
    for old, new in button_fixes:
        content = content.replace(old, new)
        
    # Remove hardcoded figures
    # In jurisdiction/[id]/page.tsx
    content = content.replace('<span className="text-3xl font-black text-emerald-400">98</span>', '<span className="text-3xl font-black text-emerald-600 dark:text-emerald-400">{context?.health_score || "100"}</span>')
    
    with open(filepath, "w") as f:
        f.write(content)
    
    print(f"Updated {filepath}")
