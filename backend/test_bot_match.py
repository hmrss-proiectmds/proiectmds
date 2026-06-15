import asyncio
import uuid
from app.database import async_session
from app.services.game import game_manager
from app.models.agent import Agent, IntegrationMode
from app.models.user import User

async def run_test():
    async with async_session() as db:
        # Get admin user
        from sqlalchemy import select
        admin = (await db.execute(select(User).limit(1))).scalar_one()

        # Create two mock agents
        a1 = Agent(
            owner_id=admin.id,
            name="Bot 1",
            game_type="chess",
            integration_mode=IntegrationMode.webhook,
            webhook_url="http://localhost:8001/play",
            elo_rating=1200
        )
        a2 = Agent(
            owner_id=admin.id,
            name="Bot 2",
            game_type="chess",
            integration_mode=IntegrationMode.webhook,
            webhook_url="http://localhost:8001/play",
            elo_rating=1200
        )
        db.add(a1)
        db.add(a2)
        await db.flush()

        print(f"Created agents {a1.id} and {a2.id}")

        session = await game_manager.create_game(
            db=db,
            game_type="chess",
            creator_id=None,
            creator_username=a1.name,
            creator_elo=a1.elo_rating,
            vs_ai=False,
            creator_is_agent=True,
            creator_webhook_url=a1.webhook_url,
            creator_agent_id=a1.id,
        )

        await game_manager.join_game(
            db=db,
            match_id=session.match_id,
            player_id=None,
            player_username=a2.name,
            player_elo=a2.elo_rating,
            is_agent=True,
            webhook_url=a2.webhook_url,
            agent_id=a2.id,
        )
        await db.commit()
        
        print("Game started!")

        while session.status == "active":
            ai_result = await game_manager.make_ai_move(db, session.match_id)
            if not ai_result:
                break
            await db.commit()
            print(f"Turn {session.engine.get_current_turn(session.state)} made a move")

        print(f"Game finished! Status: {session.status}, Result: {session.result}")

if __name__ == "__main__":
    asyncio.run(run_test())
