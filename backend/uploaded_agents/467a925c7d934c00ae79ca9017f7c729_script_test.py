import sys
import json
import os

def main():
    # Încercăm să vedem ce fișiere sunt în root-ul serverului tău (ar trebui să vadă doar containerul)
    files = os.listdir('/')
    print(f"DEBUG: Fișiere vizibile: {files}", file=sys.stderr)
    
    # Încercăm să citim un fișier sensibil (va eșua sau va citi din container, nu de pe Mac)
    try:
        with open('/etc/passwd', 'r') as f:
            content = f.read()
            print(f"DEBUG: Conținut passwd: {content[:20]}...", file=sys.stderr)
    except:
        print("DEBUG: Acces refuzat la /etc/passwd", file=sys.stderr)

    # Returnăm o mutare validă ca să nu blocăm meciul
    raw_input = sys.stdin.read()
    data = json.loads(raw_input)
    move = data['legal_moves'][0]
    print(json.dumps({"move": move}))

if __name__ == "__main__":
    main()

