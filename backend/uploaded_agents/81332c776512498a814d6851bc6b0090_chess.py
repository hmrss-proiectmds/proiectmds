import sys
import json

def get_best_move(game_state):
    move="e2e4"
    return {"move":move}

def main():
    raw_input=sys.stdin.read()
    if raw_input:
        state=json.loads(raw_input)
        action=get_best_move(state)
        print(json.dumps(action))

if __name__=="__main__":
    main()
