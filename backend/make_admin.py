import asyncio
import sys
from sqlalchemy import select
from app.database import async_session
from app.models.user import User, UserRole

async def main():
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <username>")
        sys.exit(1)
        
    username = sys.argv[1]
    
    async with async_session() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if not user:
            print(f"Error: User '{username}' not found. Please register first.")
            sys.exit(1)
            
        user.role = UserRole.admin
        await db.commit()
        print(f"Success! User '{username}' is now an Admin.")

if __name__ == "__main__":
    asyncio.run(main())
