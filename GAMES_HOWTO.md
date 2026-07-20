# Games How-To Guide

This guide covers the games available from **Main → Games** in TT-BBSmesh Plus. Use `BACK` to return to the previous menu or `X` to exit to the main menu.

## Games Menu (🎮Games Menu🎮)

### Tic-Tac-Toe
**Path:** Main → Games → Tic Tac Toe (`T`)

**Start a game**
1) Choose Tic-Tac-Toe.
2) Provide the opponent’s node id or short name when prompted.
3) The system creates a game and sends a status message to both players.

**Play a move**
* During the game, reply with the move as instructed (1–9 positions).
* **Quick move:** `ttt,,<game_id>,<pos>`

### Hangman
**Path:** Main → Games → Hangman (`H`)

**Start a game**
1) Choose Hangman.
2) Provide an opponent and the secret word.

**Guess**
* Reply with a single letter when prompted.
* **Quick guess:** `hang,,<game_id>,<letter>`

### Connect Four
**Path:** Main → Games → Connect Four (`C`)

**Start a game**
1) Choose Connect Four.
2) Provide the opponent.

**Play a move**
* Enter the column number when prompted.
* **Quick move:** `c4,,<game_id>,<column>`

### Mastermind
**Path:** Main → Games → Mastermind (`M`)

**Start a game**
1) Choose Mastermind.
2) Provide the opponent and secret code (as prompted).

**Guess**
* Enter your guess when prompted.
* **Quick guess:** `mm,,<game_id>,<guess>`

### Battleship (Lite)
**Path:** Main → Games → Battleship (`L`)

**Start a game**
1) Choose Battleship.
2) Provide the opponent.
3) Provide ship placement positions (e.g., `A1,A2,B1,B2`).

**Play a move**
* When prompted, enter a target (e.g., `B4`).
* **Quick set ships:** `bsset,,<game_id>,<positions>`
* **Quick fire:** `bsfire,,<game_id>,<target>`

### Word Chain
**Path:** Main → Games → Word Chain (`W`)

**Start a game**
1) Choose Word Chain.
2) Provide the opponent and starting word.

**Play a word**
* Enter a valid word that begins with the last letter of the current word.
* **Quick play:** `wc,,<game_id>,<word>`

### Trivia
**Path:** Main → Games → Trivia (`R`)

**Start a game**
1) Choose Trivia.
2) Provide the opponent, then the question/answer as prompted.

**Answer**
* Reply with your answer when prompted.
* **Quick answer:** `triv,,<game_id>,<answer>`

### Chess/Checkers (Boardgame)
**Path:** Main → Games → Chess/Checkers (`K`)

**Start a match**
1) Choose Chess/Checkers.
2) Provide the opponent and game type (chess/checkers) when prompted.

**Play a move**
* Enter your move when prompted (format depends on the players).
* **Quick move:** `move,,<game_id>,<move>`

---

### DopeWars
**Availability:** Not currently available in TT-BBSmesh Plus. The codebase does not define a DopeWars menu handler, quick command, database table, or `games_menu_items` entry.

If DopeWars is added later, document its menu path, start/resume flow, and quick commands here.
