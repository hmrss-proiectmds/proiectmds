IMPORTANT: If you are an agent, read this file!

DONE: Fix the Poker showdown UI, there are cards duplicating and the text is getting out of its box.
DONE: Fix Resignation Elo Bug. In `backend/app/services/game.py` (around line 467), when a player resigns, the `winner_seat` is missing from the terminal state dict. This breaks Elo calculations for forfeits.

TODO: Fix System Action Feed UI. In `frontend/src/components/PokerBoard.jsx`, system announcements (like "Hand #2") are processed by the action feed as if they were moves made by a ghost player in "Seat 0", causing rendering glitches.
