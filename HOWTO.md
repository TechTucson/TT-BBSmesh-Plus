# BBS User How-To Guide

This guide explains how to use every available menu item and quick command in the TT-BBSmesh Plus application. All interactions are done by sending **direct messages** to the node running the BBS server. Whenever you are unsure, send `BACK` to return to the previous menu or `X` to exit to the main menu.

## General navigation

* **Main menu**: Send any message to the BBS node to receive it.
* **Pick an option**: Reply with the letter/number shown in brackets (e.g., `M` for `[M]ail`).
* **Follow prompts**: When the system asks a question (like replying to a message), your reply is used for that flow until you return to a menu.
* **Back/exit**: Send `BACK` to return to the prior menu or `X` to go to the main menu.

---

## Main Menu (💾TC² BBS💾)

Main menu entries are configured in `config.ini`, but the standard items include:

* **[Q]uick Commands** → shows quick command shortcuts.
* **[B]BS** → BBS menu (mail, bulletins, channels, JS8Call).
* **[U]tilities** → tools like stats, time, dictionary, weather.
* **[G]ames** → games menu.
* **[R]eadiness** → readiness check-in, roster, go-bag, radio reference.
* **E[X]IT** → back to main menu.

---

## BBS Menu (📰BBS Menu📰)

### Mail
**Path:** Main → BBS → Mail (`M`)

**Read mail**
1) Choose `R` at the mail menu.
2) The system lists mail IDs. Reply with the mail ID to read it.
3) After reading, you may be prompted to delete the message.

**Send mail (menu flow)**
1) Choose `S` at the mail menu.
2) Provide the recipient’s short name.
3) Provide a subject.
4) Provide the message body.
5) The system sends the mail and returns to the menu.

**Quick send mail**
* **Command:** `sm,,<short_name>,<subject>,<message>`
* Example: `sm,,N0CALL,Hello,Meet at 7pm.`

**Quick check mail**
* **Command:** `cm`

### Bulletins
**Path:** Main → BBS → Bulletins (`L`)

1) Choose a board:
   * `G` = General
   * `I` = Info
   * `N` = News
   * `U` = Urgent
2) Choose what to do:
   * `R` = Read posts
   * `P` = Post a new bulletin

**Read a bulletin (menu flow)**
1) Choose `R` after selecting the board.
2) The system lists bulletin IDs. Reply with the ID to read it.

**Post a bulletin (menu flow)**
1) Choose `P` after selecting the board.
2) Provide a subject.
3) Provide the message content.

**Quick post bulletin**
* **Command:** `pb,,<board>,<subject>,<message>`
* Board values: `General`, `Info`, `News`, `Urgent`
* Example: `pb,,General,Net Tonight,Join the net at 1900 local.`

**Quick check bulletins**
* **Command:** `cb,,<board>`
* Example: `cb,,General`

### Channel Directory
**Path:** Main → BBS → Channel Dir (`C`)

**Read channels (menu flow)**
1) Choose the read/list option (shown in the menu).
2) The system lists channel IDs. Reply with the ID to read details.

**Add a channel (menu flow)**
1) Choose the add/post option (shown in the menu).
2) Provide the channel name.
3) Provide the channel URL.

**Quick add channel**
* **Command:** `chp,,<name>,<url>`
* Example: `chp,,Local Mesh,https://example.com/mesh`

**Quick list channels**
* **Command:** `chl`

### JS8Call
**Path:** Main → BBS → JS8Call (`J`)

**Group messages**
1) Choose `G`.
2) Select the group number to view messages.

**Station messages**
1) Choose `S` to list messages for this station.

**Urgent messages**
1) Choose `U` to list urgent JS8Call messages.

---

## Utilities Menu (🛠️Utilities Menu🛠️)

### Stats
**Path:** Main → Utilities → Stats (`S` or `1`)

Follow the prompts to request the stats view you want (node stats or general stats).

### Fortune
**Path:** Main → Utilities → Fortune (`F` or `2`)

Displays a random fortune from `fortunes.txt`.

### Wall of Shame
**Path:** Main → Utilities → Wall of Shame (`W` or `3`)

Displays nodes with low battery (based on available log data).

### Time
**Path:** Main → Utilities → Time (`T` or `4`)

Returns the current server time.

### Sun/Moon
**Path:** Main → Utilities → Sun/Moon (`N` or `5`)

Returns sunrise/sunset information based on configured location.

### Dictionary
**Path:** Main → Utilities → Define (`D` or `6`)

1) Choose the dictionary option.
2) Enter the word to define.

### ADS-B
**Path:** Main → Utilities → ADSB (`A` or `7`)

1) Choose ADS-B.
2) Pick the mode (latest, last 10, or alert) when prompted.

### Ollama (LLM)
**Path:** Main → Utilities → Ollama (`O` or `8`)

1) Choose Ollama.
2) Enter your prompt. The response is returned in chat.

### Weather (WX)
**Path:** Main → Utilities → Weather (`H` or `9`)

1) Choose Weather.
2) Follow prompts to request recent entries from the weather system.

---

## Readiness Menu (🧭Readiness Menu🧭)

### Check-In
**Path:** Main → Readiness → Check-In (`C`)

1) Choose Check-In.
2) Enter your status (e.g., OK, NEED HELP).
3) Optionally add a note.
4) The system records your check-in and returns to the menu.

### Team Roster
**Path:** Main → Readiness → Team Roster (`T`)

Roster flow options are presented in the menu. Typical actions include:

* **View roster**: lists roster entries.
* **Add/update roster entry**: provide short name, node id, and role.
* **Delete roster entry**: remove an entry.

Follow the prompts for each step.

### Go-Bag Checklist
**Path:** Main → Readiness → Go-Bag (`G`)

Displays the go-bag checklist items.

**Update the checklist text**
Edit `GO_BAG_CHECKLIST` in `command_handlers.py`. Each line is a quoted string with a `\n` at the end. Restart the server after saving changes.

### Radio/Comms Reference
**Path:** Main → Readiness → Radio Reference (`R`)

Displays the radio/comms quick reference template.

**Update the radio/comms reference**
Edit `RADIO_REFERENCE` in `command_handlers.py`. Each line is a quoted string with a `\n` at the end. Restart the server after saving changes.

---

## Database Cleanup & Backup (CLI)

You can clear the SQLite database before startup using the server CLI flag. This is useful for resetting the BBS data during development or testing.

**Commands**

```
python3 server.py --cleandb
```

```
python3 server.py --dbbackup
```

```
python3 server.py --dbbackup /path/to/backup.db
```

**Notes**
* This removes the existing database contents before the server initializes a fresh database.
* Use with caution—this is destructive and cannot be undone.
* When you run `--cleandb`, the server prompts you to back up the database first.
* `--dbbackup` creates a timestamped backup by default, or uses the path you supply.
**Notes**
* This removes the existing database contents before the server initializes a fresh database.
* Use with caution—this is destructive and cannot be undone.

---

## Games Menu (🎮Games Menu🎮)

The games instructions now live in [GAMES_HOWTO.md](GAMES_HOWTO.md).

Current in-app games include Tic-Tac-Toe, Hangman, Connect Four, Mastermind, Battleship (Lite), Word Chain, Trivia, and Chess/Checkers. DopeWars is **not currently available** in the application.

## Quick Command Reference

You can send these commands directly (without navigating menus):

* **Send mail:** `sm,,<short_name>,<subject>,<message>`
* **Post bulletin:** `pb,,<board>,<subject>,<message>`
* **Check bulletins:** `cb,,<board>`
* **List channels:** `chl`
* **Post channel:** `chp,,<name>,<url>`
* **Tic-Tac-Toe move:** `ttt,,<game_id>,<pos>`
* **Check mail:** `cm`
* **Hangman guess:** `hang,,<game_id>,<letter>`
* **Connect Four move:** `c4,,<game_id>,<column>`
* **Mastermind guess:** `mm,,<game_id>,<guess>`
* **Battleship set ships:** `bsset,,<game_id>,<positions>`
* **Battleship fire:** `bsfire,,<game_id>,<target>`
* **Word Chain play:** `wc,,<game_id>,<word>`
* **Trivia answer:** `triv,,<game_id>,<answer>`
* **Boardgame move:** `move,,<game_id>,<move>`
