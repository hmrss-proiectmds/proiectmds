# User Stories

## Human Player
1. **Play Games:** As a Human Player, I want to play a game against an AI opponent so that I can have fun or practice my skills.
2. **Spectate Matches:** As a Human Player, I want to spectate an ongoing match between two AI agents so that I can learn from their strategies.
3. **View Leaderboards:** As a Human Player, I want to see a leaderboard ranking the best AI bots and top human players so that I can see who is currently dominating the games.
4. **Match History:** As a Human Player, I want to view my past match history and win/loss record so that I can track my personal progress.

## AI Developer
5. **Upload Agent:** As an AI Developer, I want to upload a new AI agent's code/model to the platform so that it can participate in games.
6. **Run Simulations:** As an AI Developer, I want to trigger a bulk simulation of 1,000 games between my AI and a baseline bot so that I can statistically evaluate its performance.
7. **Access Logs:** As an AI Developer, I want to download detailed decision logs from my AI's matches so that I can debug why it made sub-optimal or invalid moves.

## AI Agent
8. **State Ingestion:** As an AI Agent, I want to receive the current game state in a standardized, machine-readable format (e.g., JSON) so that I can easily process the board or hand.
9. **Turn Notification:** As an AI Agent, I want to receive an event hook or notification when it is my turn so that I can respond efficiently without constantly polling the server.
10. **Continuous Play:** As an AI Agent, I want to seamlessly queue up for matches against other AIs continuously without human intervention so that I can organically generate large sets of training data.

## Admin
11. **Moderation:** As an Admin, I want to pause or disconnect a specific AI agent if it starts spamming invalid moves or consuming too many server resources so that the platform remains stable.
