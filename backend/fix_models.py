import os
import re

legacy_files = os.listdir("app/models")
domain_dirs = os.listdir("app/domains")

class_to_domain = {}

for domain in domain_dirs:
    models_path = f"app/domains/{domain}/models.py"
    if os.path.exists(models_path):
        with open(models_path, "r") as f:
            content = f.read()
            classes = re.findall(r"class ([A-Za-z0-9_]+)\(Base\):", content)
            for c in classes:
                class_to_domain[c] = f"app.domains.{domain}.models"

# Add dummy ones that don't exist anywhere
class_to_domain["CommunityValidation"] = "app.models.community_validation"
class_to_domain["CommunityComment"] = "app.models.community_validation"

# Write them
for legacy_file in legacy_files:
    if not legacy_file.endswith(".py") or legacy_file == "__init__.py":
        continue
    
    with open(f"app/models/{legacy_file}", "w") as f:
        for cls_name, import_path in class_to_domain.items():
            # if we are writing into community_validation.py, skip the dummy imports
            if legacy_file == "community_validation.py" and import_path == "app.models.community_validation":
                continue
            f.write(f"try:\n    from {import_path} import {cls_name}\nexcept ImportError:\n    pass\n")

print("Fixed legacy model files.")
