import sys
import json
import random

def main():
    # 1. Citim payload-ul (starea jocului) trimis de platformă pe standard input (stdin)
    input_data = sys.stdin.read()
    
    if not input_data:
        # Dacă nu am primit nimic, returnăm o eroare (nu se va întâmpla în producție)
        print(json.dumps({"error": "No input provided"}))
        return

    try:
        # 2. Parsăm datele JSON primite
        state = json.loads(input_data)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        return

    # 3. Extragem mutările legale posibile
    legal_moves = state.get("legal_moves", [])
    
    if not legal_moves:
        # Nu avem mutări (ex: e șah-mat)
        print(json.dumps({"move": ""}))
        return

    # 4. LOGICA BOTULUI: Aici decizi ce mutare să faci!
    # Variabile utile primite în "state":
    # - state["board"] -> aranjamentul tablei
    # - state["turn_seat"] -> al cui e rândul
    # - state["is_check"] -> ești în șah? (doar la șah)
    #
    # Deocamdată facem o alegere aleatorie din mutările perfect legale:
    chosen_move = random.choice(legal_moves)
    
    # 5. Returnăm decizia printând rezultatul ca un string JSON pe stdout
    output = {
        "move": chosen_move
    }
    
    # Platforma va citi exact acest print! Nu folosi print() pentru debug normal,
    # deoarece va corupe formatul JSON pe care platforma îl așteaptă.
    print(json.dumps(output))

if __name__ == "__main__":
    main()
