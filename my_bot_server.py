import random
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI(title="My Real Webhook Bot")

@app.post("/play")
async def play_move(request: Request):
    # 1. Citim ce ne trimite platforma
    data = await request.json()
    
    # Platforma ne dă tabla de șah și mutările legale (ex: ["e2e4", "g1f3", ...])
    legal_moves = data.get("legal_moves", [])
    
    if not legal_moves:
        return {"move": ""} # Nu avem ce muta (șah mat)

    # 2. LOGICA BOTULUI (aici pui tu cod de Inteligență Artificială în viitor)
    # Deocamdată botul nostru alege la întâmplare una din mutările perfect legale
    chosen_move = random.choice(legal_moves)
    
    print(f"🤖 A venit rândul meu! Am analizat tabla și am ales mutarea: {chosen_move}")
    
    # 3. Returnăm răspunsul exact așa cum îl așteaptă platforma ta
    return {"move": chosen_move}

if __name__ == "__main__":
    # Rulăm botul pe portul 8001 (platforma ta principală e pe 8000)
    print("🚀 Botul a pornit și așteaptă semnale de la joc la http://127.0.0.1:8001/play")
    uvicorn.run(app, host="127.0.0.1", port=8001)
