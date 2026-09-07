"""
Adds investments.read and investments.write permissions and grants them to the admin role.
Run with: .\env\Scripts\python.exe seed_permissions.py
"""
import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models import Permission, Role, RolePermission

NEW_PERMISSIONS = [
    {"name": "investments.read", "module": "investments", "description": "View investment portfolio"},
    {"name": "investments.write", "module": "investments", "description": "Create and manage investments"},
]

async def seed():
    async with SessionLocal() as session:
        # Find admin role
        admin_role = await session.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is None:
            # Try first role available
            admin_role = await session.scalar(select(Role).limit(1))
        if admin_role is None:
            print("No role found. Please create a role first.")
            return

        for perm_data in NEW_PERMISSIONS:
            # Check if permission already exists
            existing = await session.scalar(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            if existing is None:
                perm = Permission(**perm_data)
                session.add(perm)
                await session.flush()
                print(f"Created permission: {perm_data['name']}")
            else:
                perm = existing
                print(f"Permission already exists: {perm_data['name']}")

            # Grant to admin role
            existing_grant = await session.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == perm.id
                )
            )
            if existing_grant is None:
                session.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))
                print(f"  -> Granted to role: {admin_role.name}")
            else:
                print(f"  -> Already granted to role: {admin_role.name}")

        await session.commit()
        print("\nDone! Investments permissions seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
