import re
import os

files_to_fix = [
    "app/api/v1/assets.py",
    "app/api/v1/auth.py",
    "app/api/v1/projects.py",
    "app/api/v1/registry.py",
    "app/domains/assets/service.py"
]

for fpath in files_to_fix:
    with open(fpath, "r") as f:
        content = f.read()

    # projects.py
    content = re.sub(r'valid_sectors = \{p\.get_metadata\(\)\["id"\] for p in plugin_registry\.list_plugins\(\)\}', 'valid_sectors = {"cookstove", "hybrid_energy", "biochar", "ev_mobility"}', content)
    
    # registry.py
    content = re.sub(r'for plugin_id, plugin in plugin_registry\._plugins\.items\(\):.*?plugins\.append\(.*?\)', 'plugins = []', content, flags=re.DOTALL)

    # auth.py
    content = re.sub(r'if not plugin_registry\.get_plugin\(sector\):.*?raise HTTPException\(status_code=400, detail="Invalid sector"\)', '', content, flags=re.DOTALL)
    
    # assets.py
    content = re.sub(r'plugin = plugin_registry\.get_plugin\(project\.sector\)\n\s+if plugin:\n\s+schema = plugin\.get_asset_schema\(\)\n\s+# validate_asset_data\(asset_in\.attributes or \{\}, schema\)\n\s+pass', '', content)
    content = re.sub(r'plugin = plugin_registry\.get_plugin\(project\.sector\)\n\s+if plugin:\n\s+schema = plugin\.get_asset_schema\(\)\n\s+# validate_asset_data\(asset_in\.attributes or \{\}, schema\)\n\s+pass', '', content)
    
    # assets service
    content = re.sub(r'plugin = plugin_registry\.get_plugin\(project_sector\)\n\s+if plugin:\n\s+schema = plugin\.get_asset_schema\(\)\n\s+# validate_asset_data\(payload\.attributes or \{\}, schema\)\n\s+pass', '', content)

    with open(fpath, "w") as f:
        f.write(content)
