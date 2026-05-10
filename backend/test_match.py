import asyncio
from app.database import async_session
from app.services.game import game_manager
from sqlalchemy import select
from app.models.agent import Agent
import uuid

async def test():
    async with async_session() as db:
        agents = (await db.execute(select(Agent).limit(2))).scalars().all()
        if len(agents) < 2:
            print("Not enough agents")
            return
        a1, a2 = agents[0], agents[1]
        try:
            session = await game_manager.create_game(
                db=db,
                game_type="chess",
                creator_id=None,
                creator_username=a1.name,
                creator_elo=a1.elo_rating,
                vs_ai=False,
                creator_is_agent=True,
                creator_agent_id=a1.id
            )
            await game_manager.join_game(
                db=db,
                match_id=session.match_id,
                player_id=None,
                player_username=a2.name,
                player_elo=a2.elo_rating,
                is_agent=True,
                agent_id=a2.id
            )
            await db.commit()
            print("SUCCESS")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
