import os
import re

files_to_fix = [
    "app/main.py",
    "app/api/v1/auth.py",
    "app/api/v1/registry.py",
    "app/api/v1/assets.py",
    "app/api/v1/projects.py",
    "app/domains/activities/service.py",
    "app/domains/assets/service.py",
    "app/services/quantification_engine.py",
    "app/domains/methodologies/services/migration_service.py"
]

def remove_plugin_usages():
    for fpath in files_to_fix:
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r') as f:
            content = f.read()

        # Remove imports
        content = re.sub(r'from app\.plugins\.registry import plugin_registry\n?', '', content)
        content = re.sub(r'from app\.plugins import initialize_plugins\n?', '', content)
        content = re.sub(r'from app\.domains\.plugin_runtime\.api import router as registry_plugins_router\n?', '', content)
        content = re.sub(r'from app\.plugins\.cookstove\.methodologies import .*?\n', '', content)
        content = re.sub(r'from app\.plugins\.cookstove\.plugin import .*?\n', '', content)
        
        # main.py specific
        content = re.sub(r'initialize_plugins\(\)\n?', '', content)
        content = re.sub(r'app\.include_router\(registry_plugins_router, prefix="/api/v1/plugins", tags=\["Plugin Runtime Architecture"\]\)\n?', '', content)

        # auth.py specific
        content = re.sub(r'if not plugin_registry\.get_plugin\(sector\):.*?raise HTTPException\(status_code=400, detail="Invalid sector"\)', '', content, flags=re.DOTALL)

        # registry.py specific
        content = re.sub(r'for plugin_id, plugin in plugin_registry\._plugins\.items\(\):.*?plugins\.append\(.*?\)', 'plugins = []', content, flags=re.DOTALL)

        # assets.py specific
        content = re.sub(r'plugin = plugin_registry\.get_plugin\(project\.sector\)\n?\s*if plugin:\n?\s*schema = plugin\.get_asset_schema\(\)\n?\s*#.*?\n?\s*pass\n?', '', content, flags=re.DOTALL)
        content = re.sub(r'plugin = plugin_registry\.get_plugin\(project\.sector\)\n?\s*if plugin:\n?\s*schema = plugin\.get_asset_schema\(\)\n?\s*#.*?\n?\s*pass\n?', '', content, flags=re.DOTALL)
        
        # projects.py specific
        content = re.sub(r'valid_sectors = \{p\.get_metadata\(\)\["id"\] for p in plugin_registry\.list_plugins\(\)\}\n?\s*if project_in\.sector not in valid_sectors:\n?\s*raise HTTPException\(status_code=400, detail=f"Invalid sector: \{project_in\.sector\}"\)\n?', '', content, flags=re.DOTALL)

        # activities service specific
        content = re.sub(r'# Resolve dynamic JSON Schema from plugin\n?\s*plugin = plugin_registry\.get_plugin\(project_sector\)\n?\s*if plugin:\n?\s*methodologies = plugin\.get_methodologies_config\(\)\n?\s*# Try to match matching methodology or default to first methodology\n?\s*meth = methodologies\[0\] if methodologies else None\n?\s*schema = meth\.get\("attributes_schema", \{\}\) if meth else \{\}\n?\s*validate_activity_data\(payload\.activity_data or \{\}, schema\)\n?', '', content, flags=re.DOTALL)

        # assets service specific
        content = re.sub(r'plugin = plugin_registry\.get_plugin\(project_sector\)\n?\s*if plugin:\n?\s*schema = plugin\.get_asset_schema\(\)\n?\s*# validate_asset_data\(payload\.attributes or \{\}, schema\)\n?\s*pass\n?', '', content, flags=re.DOTALL)
        
        with open(fpath, 'w') as f:
            f.write(content)

remove_plugin_usages()
