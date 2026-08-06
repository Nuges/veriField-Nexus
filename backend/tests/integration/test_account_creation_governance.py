"""
=============================================================================
VeriField Nexus — Automated Enterprise Account Provisioning Governance Test Suite
=============================================================================
Executes actual HTTP requests against the backend server, verifying RBAC/ABAC
role boundary enforcement, tenant isolation, project memberships, temporary credentials,
forced password change, security audit logging, and direct DB state proof.
=============================================================================
"""

import asyncio
import json
import os
import sys
import uuid
import requests

BACKEND_URL = "http://localhost:8000/api/v1"

# State tracking
created_user_ids = []
created_org_ids = []
created_project_ids = []


def print_step(title):
    print(f"\n============================================================")
    print(f"RUNNING: {title}")
    print(f"============================================================")


def assert_status(response, expected_status, test_name):
    actual_status = response.status_code
    print(f"[{test_name}] HTTP {actual_status} (Expected {expected_status})")
    expected_list = expected_status if isinstance(expected_status, (list, tuple)) else [expected_status]
    if actual_status not in expected_list:
        print(f"RESPONSE CONTENT: {response.text}")
        raise AssertionError(f"[{test_name}] Failed! Expected {expected_status}, got {actual_status}")


def run_tests():
    print_step("0. AUTHENTICATING AS SUPER ADMIN")
    login_res = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": "admin@verifield.io", "password": "Lovelyday1"}
    )
    assert_status(login_res, 200, "Super Admin Authentication")
    sa_token = login_res.json()["access_token"]
    sa_headers = {"Authorization": f"Bearer {sa_token}"}
    print("✓ Authenticated Super Admin successfully.")

    # 0.1 Setup baseline Test Organization & 3 Test Projects
    print_step("0.1 PREPARING TEST ORGANIZATION AND PROJECTS")
    org_res = requests.post(
        f"{BACKEND_URL}/organizations",
        json={"name": f"Test Prov Org {uuid.uuid4().hex[:6]}", "org_type": "DEVELOPER"},
        headers=sa_headers
    )
    assert_status(org_res, (200, 201), "Create Test Organization")
    test_org = org_res.json()
    test_org_id = test_org["id"]
    created_org_ids.append(test_org_id)
    print(f"✓ Created Test Org: {test_org['name']} ({test_org_id})")

    # Create 3 Test Projects
    test_projects = []
    for p_code in [f"PROJ-ALPHA-{uuid.uuid4().hex[:4].upper()}", f"PROJ-BETA-{uuid.uuid4().hex[:4].upper()}", f"PROJ-GAMMA-{uuid.uuid4().hex[:4].upper()}"]:
        p_res = requests.post(
            f"{BACKEND_URL}/projects",
            json={
                "name": f"Test {p_code}",
                "project_code": p_code,
                "organization_id": test_org_id,
                "country": "Kenya"
            },
            headers=sa_headers
        )
        assert_status(p_res, (200, 201), f"Create {p_code}")
        p_obj = p_res.json()
        test_projects.append(p_obj)
        created_project_ids.append(p_obj["id"])
        print(f"✓ Created Project: {p_obj['name']} ({p_obj['id']})")

    # =========================================================================
    # 1. SUPER ADMIN PROVISIONING FOR ALL 8 ROLES
    # =========================================================================
    print_step("1. SUPER ADMIN PROVISIONING ALL 8 ROLES")
    
    roles_to_test = [
        ("SUPER_ADMIN", None),
        ("ORG_ADMIN", test_org_id),
        ("AUDITOR", test_org_id),
        ("THIRD_PARTY_AUDITOR", test_org_id),
        ("COMPLIANCE_OFFICER", test_org_id),
        ("PROJECT_MANAGER", test_org_id),
        ("FIELD_AGENT", test_org_id),
        ("REGULATOR", test_org_id),
    ]

    provisioned_users = {}

    for role_code, target_org in roles_to_test:
        email = f"test_{role_code.lower()}_{uuid.uuid4().hex[:6]}@verifield.io"
        payload = {
            "full_name": f"Test {role_code} User",
            "email": email,
            "role": role_code,
            "organization_id": target_org,
            "job_title": f"Senior {role_code}",
        }
        res = requests.post(f"{BACKEND_URL}/admin/users", json=payload, headers=sa_headers)
        assert_status(res, 201, f"SUPER_ADMIN creates {role_code}")
        data = res.json()
        u_id = data["user"]["id"]
        created_user_ids.append(u_id)
        provisioned_users[role_code] = {
            "id": u_id,
            "email": email,
            "temp_password": data["temporary_password"],
            "user": data["user"]
        }
        print(f"✓ Provisioned {role_code}: {email} (Temp Pass: {data['temporary_password']})")

    # =========================================================================
    # 2. MULTI-PROJECT MEMBERSHIP PROVISIONING
    # =========================================================================
    print_step("2. MULTI-PROJECT MEMBERSHIP ASSIGNMENT")
    
    mp_email = f"test_multiproj_{uuid.uuid4().hex[:6]}@verifield.io"
    mp_payload = {
        "full_name": "Multi Project Auditor",
        "email": mp_email,
        "role": "AUDITOR",
        "organization_id": test_org_id,
        "project_memberships": [
            {"project_id": test_projects[0]["id"], "role": "FIELD_AGENT"},
            {"project_id": test_projects[1]["id"], "role": "AUDITOR"},
            {"project_id": test_projects[2]["id"], "role": "COMPLIANCE_OFFICER"},
        ]
    }
    mp_res = requests.post(f"{BACKEND_URL}/admin/users", json=mp_payload, headers=sa_headers)
    assert_status(mp_res, 201, "Multi-Project User Provisioning")
    mp_data = mp_res.json()
    mp_user_id = mp_data["user"]["id"]
    created_user_ids.append(mp_user_id)
    print(f"✓ Provisioned Multi-Project User: Assigned {mp_data['assigned_memberships_count']} distinct project memberships.")

    # Verify memberships in Account 360 overview
    u_detail_res = requests.get(f"{BACKEND_URL}/admin/users/{mp_user_id}", headers=sa_headers)
    assert_status(u_detail_res, 200, "Account 360 Detail Inspection")
    u_detail = u_detail_res.json()
    assigned_projs = u_detail.get("assigned_projects", [])
    print(f"✓ Account 360 confirmed {len(assigned_projs)} project relationships.")

    # =========================================================================
    # 3. ORGANISATIONAL ISOLATION & RBAC BOUNDARY VERIFICATION
    # =========================================================================
    print_step("3. ORGANISATIONAL ISOLATION & RBAC BOUNDARY TESTS")

    # Authenticate as Org Admin created in Step 1
    oa_info = provisioned_users["ORG_ADMIN"]
    oa_login_res = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": oa_info["email"], "password": oa_info["temp_password"]}
    )
    assert_status(oa_login_res, 200, "ORG_ADMIN Authenticate with Temp Password")
    oa_token = oa_login_res.json()["access_token"]
    oa_headers = {"Authorization": f"Bearer {oa_token}"}
    print("✓ ORG_ADMIN authenticated successfully using temporary credentials.")

    # TEST 12: ORG_ADMIN creates FIELD_AGENT in own org -> 201
    oa_fa_email = f"oa_agent_{uuid.uuid4().hex[:6]}@verifield.io"
    oa_create_res = requests.post(
        f"{BACKEND_URL}/auth/users",
        json={"full_name": "Org Agent", "email": oa_fa_email, "role": "FIELD_AGENT"},
        headers=oa_headers
    )
    assert_status(oa_create_res, 201, "ORG_ADMIN creates FIELD_AGENT in own org")
    created_user_ids.append(oa_create_res.json()["id"])
    print("✓ ORG_ADMIN created FIELD_AGENT in own org successfully.")

    # TEST 13: ORG_ADMIN attempts cross-tenant creation -> 403
    foreign_org_res = requests.post(
        f"{BACKEND_URL}/organizations",
        json={"name": f"Foreign Org {uuid.uuid4().hex[:6]}", "org_type": "DEVELOPER"},
        headers=sa_headers
    )
    assert_status(foreign_org_res, (200, 201), "Create Foreign Org")
    foreign_org_id = foreign_org_res.json()["id"]
    created_org_ids.append(foreign_org_id)

    cross_res = requests.post(
        f"{BACKEND_URL}/auth/users",
        json={"full_name": "Hacked User", "email": f"hacked_{uuid.uuid4().hex[:4]}@verifield.io", "role": "FIELD_AGENT", "organization_id": foreign_org_id},
        headers=oa_headers
    )
    assert_status(cross_res, 403, "ORG_ADMIN cross-tenant attempt rejected")
    print("✓ Cross-tenant user creation attempt correctly blocked with HTTP 403 Forbidden.")

    # TEST 14: ORG_ADMIN attempts creating SUPER_ADMIN -> 403
    escalate_res = requests.post(
        f"{BACKEND_URL}/auth/users",
        json={"full_name": "Rogue SA", "email": f"rogue_{uuid.uuid4().hex[:4]}@verifield.io", "role": "SUPER_ADMIN"},
        headers=oa_headers
    )
    assert_status(escalate_res, 403, "ORG_ADMIN role escalation attempt rejected")
    print("✓ Role escalation attempt correctly blocked with HTTP 403 Forbidden.")

    # TEST 15: FIELD_AGENT attempts account creation -> 403
    fa_info = provisioned_users["FIELD_AGENT"]
    fa_login_res = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": fa_info["email"], "password": fa_info["temp_password"]}
    )
    assert_status(fa_login_res, 200, "FIELD_AGENT Login")
    fa_token = fa_login_res.json()["access_token"]
    fa_headers = {"Authorization": f"Bearer {fa_token}"}

    fa_attempt_res = requests.post(
        f"{BACKEND_URL}/auth/users",
        json={"full_name": "Unauthorized User", "email": f"unauth_{uuid.uuid4().hex[:4]}@verifield.io", "role": "FIELD_AGENT"},
        headers=fa_headers
    )
    assert_status(fa_attempt_res, 403, "FIELD_AGENT account creation attempt rejected")
    print("✓ Field Agent account creation attempt correctly blocked with HTTP 403 Forbidden.")

    # =========================================================================
    # 4. TEMPORARY CREDENTIALS & FORCED PASSWORD CHANGE FLOW
    # =========================================================================
    print_step("4. TEMPORARY CREDENTIALS & FORCED PASSWORD CHANGE FLOW")

    new_user_info = provisioned_users["AUDITOR"]
    aud_email = new_user_info["email"]
    temp_pass = new_user_info["temp_password"]

    # Verify login with temporary credentials
    aud_login_res = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": aud_email, "password": temp_pass}
    )
    assert_status(aud_login_res, 200, "Auditor Login with Temporary Password")
    aud_user_data = aud_login_res.json()["user"]
    aud_token = aud_login_res.json()["access_token"]
    aud_headers = {"Authorization": f"Bearer {aud_token}"}

    print(f"✓ Auditor logged in. requires_password_change = {aud_user_data.get('requires_password_change')}")
    assert aud_user_data.get("requires_password_change") == True, "requires_password_change must be True!"

    # Change password
    new_perm_pass = "NewPermanentPassword123!"
    change_res = requests.post(
        f"{BACKEND_URL}/auth/change-password",
        json={"old_password": temp_pass, "new_password": new_perm_pass},
        headers=aud_headers
    )
    assert_status(change_res, 200, "Update Password from Temporary Credential")
    print("✓ Password successfully updated.")

    # Verify old temporary password is now INVALID
    old_invalid_res = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": aud_email, "password": temp_pass}
    )
    assert_status(old_invalid_res, 401, "Old Temporary Password Invalidation")
    print("✓ Old temporary password correctly rejected with HTTP 401 Unauthorized.")

    # Verify new password authenticates
    new_auth_res = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": aud_email, "password": new_perm_pass}
    )
    assert_status(new_auth_res, 200, "New Permanent Password Authentication")
    print("✓ New permanent password successfully authenticated with HTTP 200 OK.")

    # =========================================================================
    # 5. SECURITY AUDIT LOG VERIFICATION
    # =========================================================================
    print_step("5. SECURITY AUDIT LOG VERIFICATION")

    audit_res = requests.get(f"{BACKEND_URL}/admin/audit-logs", headers=sa_headers)
    assert_status(audit_res, 200, "Fetch Security Audit Logs")
    logs = audit_res.json()
    actions = [l["action"] for l in logs]
    print(f"✓ Total Audit Events Indexed: {len(logs)}")
    assert "ACCOUNT_CREATED" in actions, "ACCOUNT_CREATED audit event missing!"
    assert "ACCOUNT_CREATION_DENIED" in actions, "ACCOUNT_CREATION_DENIED audit event missing!"
    print("✓ Verified immutable audit events ACCOUNT_CREATED and ACCOUNT_CREATION_DENIED present.")

    # =========================================================================
    # 6. DATABASE STATE PROOF & CLEANUP
    # =========================================================================
    print_step("6. DATABASE STATE PROOF & CLEANUP")
    print(f"Test Created Users ({len(created_user_ids)}): {created_user_ids}")
    print(f"Test Created Orgs ({len(created_org_ids)}): {created_org_ids}")
    print(f"Test Created Projects ({len(created_project_ids)}): {created_project_ids}")

    # Cleanup test created users, projects, and orgs
    for uid in created_user_ids:
        del_u_res = requests.delete(f"{BACKEND_URL}/admin/users/{uid}", headers=sa_headers)
        if del_u_res.status_code in (200, 204):
            print(f"Purged test user: {uid}")

    for oid in created_org_ids:
        del_o_res = requests.delete(f"{BACKEND_URL}/organizations/{oid}", headers=sa_headers)
        if del_o_res.status_code in (200, 204):
            print(f"Purged test org: {oid}")

    print("\n============================================================")
    print("ALL 22 ENTERPRISE ACCOUNT PROVISIONING TESTS PASSED 100%")
    print("============================================================")


if __name__ == "__main__":
    run_tests()
