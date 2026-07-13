import sys
from app.core.rbac import has_permission, ROLE_PLATFORM_SUPER_ADMIN, ROLE_FIELD_AGENT, ROLE_JURISDICTION_ADMIN, ROLE_ORG_OWNER

def validate_security():
    print("Starting Stream 4 & 5 Security Validation...")
    
    print("1. Validating RBAC Matrix...")
    
    # Super Admin tests
    if not has_permission(ROLE_PLATFORM_SUPER_ADMIN, "admin:all"):
        print("FAILED: SUPER_ADMIN missing admin:all")
        sys.exit(1)
        
    # Field Agent tests
    if not has_permission(ROLE_FIELD_AGENT, "activity:create"):
        print("FAILED: FIELD_AGENT missing activity:create")
        sys.exit(1)
    if has_permission(ROLE_FIELD_AGENT, "project:update"):
        print("FAILED: FIELD_AGENT has project:update")
        sys.exit(1)
        
    # Jurisdiction Admin tests
    if not has_permission(ROLE_JURISDICTION_ADMIN, "jurisdiction:all"):
        print("FAILED: JURISDICTION_ADMIN missing jurisdiction:all")
        sys.exit(1)
        
    # Org Owner tests
    if not has_permission(ROLE_ORG_OWNER, "org:manage"):
        print("FAILED: ORG_OWNER missing org:manage")
        sys.exit(1)

    print("RBAC Matrix verified.")
    print("Enterprise Security Validation Passed.")
    return True

if __name__ == "__main__":
    validate_security()
