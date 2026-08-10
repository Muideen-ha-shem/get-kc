"""One-off QA fixture seed — NOT part of the running app.

Run manually against a dev/staging Supabase project to populate realistic
data for end-to-end acceptance testing: 5 workspaces (branding, enabled
products, a workspace admin, three support agents, two customers each),
plus one platform Super Admin. Every auth user is created via the Admin
Auth API with ``email_confirm=True`` so no confirmation emails need to be
clicked before signing in.

Idempotent: safe to re-run. Auth users are looked up by email if creation
fails on a duplicate; workspaces are looked up by slug the same way.

Usage:
    venv/bin/python scripts/seed_qa_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sb import get_admin_client  # noqa: E402
from src.services.admin.platform_admin_service import PlatformAdminService  # noqa: E402
from src.services.admin.product_service import ProductService  # noqa: E402
from src.services.admin.tenant_repository import AdminWorkspaceRepository  # noqa: E402
from src.services.admin.tenant_service import TenantService  # noqa: E402
from src.services.admin.workspace_admin_service import WorkspaceAdminService  # noqa: E402
from src.services.agents.agent_repository import AgentRepository  # noqa: E402
from src.services.agents.agent_service import AgentService  # noqa: E402
from src.services.profile.profile_service import ProfileService  # noqa: E402

SEED_PASSWORD = "HavisIQ!Test2026"

admin_client = get_admin_client()
tenant_service = TenantService(repository=AdminWorkspaceRepository(client=admin_client))
product_service = ProductService()
workspace_admin_service = WorkspaceAdminService()
platform_admin_service = PlatformAdminService()
agent_service = AgentService(repository=AgentRepository(client=admin_client))
profile_service = ProfileService(client=admin_client)

created_accounts: list[dict] = []


def get_or_create_auth_user(email: str, full_name: str) -> str:
    try:
        resp = admin_client.auth.admin.create_user(
            {
                "email": email,
                "password": SEED_PASSWORD,
                "email_confirm": True,
                "user_metadata": {"full_name": full_name},
            }
        )
        return resp.user.id
    except Exception as exc:  # noqa: BLE001 — broad: any "already exists" shape from gotrue
        if "already" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise
        for user in admin_client.auth.admin.list_users():
            if (user.email or "").lower() == email.lower():
                return user.id
        raise RuntimeError(f"Could not find or create user for {email}") from exc


def get_or_create_workspace(slug: str, name: str, actor_auth_user_id: str):
    for workspace in tenant_service.list_workspaces():
        if workspace.slug == slug:
            return workspace
    return tenant_service.create_workspace(slug, name, host=None, actor_auth_user_id=actor_auth_user_id)


def seed_workspace(
    *,
    slug: str,
    name: str,
    primary_color: str,
    welcome_message: str,
    products: list[str],
    email_domain: str,
    admin_name: str,
    agents: list[tuple[str, str]],  # (name, department)
    customers: list[str],
    actor_auth_user_id: str,
) -> None:
    workspace = get_or_create_workspace(slug, name, actor_auth_user_id)
    tenant_service.update_branding(
        workspace.id,
        actor_auth_user_id,
        primary_color=primary_color,
        welcome_message=welcome_message,
    )
    for product_id in products:
        product_service.set_enabled(workspace.id, product_id, True)

    admin_email = f"{_slugify(admin_name)}@{email_domain}"
    admin_user_id = get_or_create_auth_user(admin_email, admin_name)
    workspace_admin_service.add_admin(workspace.id, admin_user_id)
    created_accounts.append(
        {"role": "workspace_admin", "workspace": name, "name": admin_name, "email": admin_email}
    )

    for agent_name, department in agents:
        agent_email = f"{_slugify(agent_name)}@{email_domain}"
        agent_user_id = get_or_create_auth_user(agent_email, agent_name)
        agent_service.get_or_create(agent_user_id, agent_email, agent_name, workspace.id, department=department)
        created_accounts.append(
            {
                "role": f"support_agent ({department})",
                "workspace": name,
                "name": agent_name,
                "email": agent_email,
            }
        )

    for customer_name in customers:
        customer_email = f"{_slugify(customer_name)}@{email_domain}"
        customer_user_id = get_or_create_auth_user(customer_email, customer_name)
        profile_service.get_or_create(customer_user_id, customer_email, customer_name, workspace_id=workspace.id)
        # get_or_create alone isn't enough: get_or_create_auth_user already
        # created the auth.users row above, firing the on_auth_user_created
        # trigger, which inserts a blank customer_profiles row (workspace_id
        # left null) before this workspace context is known — get_or_create
        # finds that row and returns it unchanged. Force-correct it (this
        # was a real, live-confirmed cross-tenant leak — see ProfileService
        # .set_workspace_id's docstring).
        profile_service.set_workspace_id(customer_user_id, workspace.id)
        created_accounts.append(
            {"role": "customer", "workspace": name, "name": customer_name, "email": customer_email}
        )

    print(f"Seeded workspace: {name} ({slug}) — id={workspace.id}, api_key={workspace.api_key}")


def _slugify(name: str) -> str:
    return name.lower().replace(" ", ".").replace("'", "")


def main() -> None:
    platform_admin_name = "Adaeze Chukwu"
    platform_admin_email = "adaeze.chukwu@ha-shem.test"
    platform_admin_user_id = get_or_create_auth_user(platform_admin_email, platform_admin_name)
    platform_admin_service.add_admin(platform_admin_user_id)
    created_accounts.append(
        {"role": "platform_super_admin", "workspace": "(global)", "name": platform_admin_name, "email": platform_admin_email}
    )

    seed_workspace(
        actor_auth_user_id=platform_admin_user_id,
        slug="ha-shem",
        name="Ha-Shem Limited",
        primary_color="#1B2A4A",
        welcome_message="Welcome to Ha-Shem — how can HavisIQ help today?",
        products=["AppManage", "STAAS", "PayCheq"],
        email_domain="ha-shem.test",
        admin_name="Chiamaka Obiora",
        agents=[
            ("Ifeoma Nnadi", "Sales"),
            ("Uche Eze", "Support"),
            ("Segun Adebayo", "Customer Success"),
        ],
        customers=["Kelechi Umeh", "Ronke Fashola"],
    )

    seed_workspace(
        actor_auth_user_id=platform_admin_user_id,
        slug="greenbank-microfinance",
        name="GreenBank Microfinance",
        primary_color="#006B3F",
        welcome_message="Welcome to GreenBank AI Assistant.",
        products=["SPIDIFY", "PayCheq", "WeCare"],
        email_domain="greenbank-microfinance.test",
        admin_name="Ngozi Eze",
        agents=[
            ("Chidi Okafor", "Sales"),
            ("Amaka Nwosu", "Support"),
            ("Tunde Bakare", "Customer Success"),
        ],
        customers=["Blessing Adeyemi", "Emeka Obi"],
    )

    seed_workspace(
        actor_auth_user_id=platform_admin_user_id,
        slug="medcare-hospital",
        name="MedCare Hospital",
        primary_color="#0E7C86",
        welcome_message="Welcome to MedCare Hospital — how can we assist you today?",
        products=["WeCare", "KwikAlert", "V-Login"],
        email_domain="medcare-hospital.test",
        admin_name="Grace Mwangi",
        agents=[
            ("Peter Otieno", "Sales"),
            ("Faith Wanjiru", "Support"),
            ("Brian Kamau", "Customer Success"),
        ],
        customers=["Susan Achieng", "David Mutua"],
    )

    # "Kestrel Peak Advisory" — a fictional consulting firm. Deliberately
    # not named after a real Big Four firm to avoid any brand-impersonation
    # concern in test fixture data.
    seed_workspace(
        actor_auth_user_id=platform_admin_user_id,
        slug="kestrel-peak-advisory",
        name="Kestrel Peak Advisory",
        primary_color="#00338D",
        welcome_message="Welcome to Kestrel Peak Advisory. How can our AI assistant help?",
        products=["Havis iReport", "Havis Xpend", "ZivaAIRA"],
        email_domain="kestrelpeak.test",
        admin_name="Oliver Bennett",
        agents=[
            ("Charlotte Hughes", "Sales"),
            ("James Whitfield", "Support"),
            ("Emily Carter", "Customer Success"),
        ],
        customers=["Robert Sinclair", "Sophie Marlowe"],
    )

    seed_workspace(
        actor_auth_user_id=platform_admin_user_id,
        slug="edusmart-academy",
        name="EduSmart Academy",
        primary_color="#F2A900",
        welcome_message="Welcome to EduSmart Academy — ask me anything about our programs!",
        products=["Havis eCertify", "ZivaAIRA", "Havis Vacay"],
        email_domain="edusmart-academy.test",
        admin_name="Thandiwe Mokoena",
        agents=[
            ("Sipho Dlamini", "Sales"),
            ("Lerato Nkosi", "Support"),
            ("Kagiso Molefe", "Customer Success"),
        ],
        customers=["Nomvula Khumalo", "Trevor van der Merwe"],
    )

    print("\n=== Seed complete ===")
    print(f"Shared password for every seeded account: {SEED_PASSWORD}\n")
    print(f"{'ROLE':<28} {'WORKSPACE':<26} {'NAME':<20} EMAIL")
    for account in created_accounts:
        print(f"{account['role']:<28} {account['workspace']:<26} {account['name']:<20} {account['email']}")


if __name__ == "__main__":
    main()
