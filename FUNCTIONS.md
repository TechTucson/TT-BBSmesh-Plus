# Functions Reference

This document catalogs every Python function in the repository and describes what it does and how to call it. The goal is to make it easy to find the right function and understand the expected inputs/outputs.

## Core flow overview

* `server.py` starts the BBS, initializes the database, and wires Meshtastic message callbacks to `message_processing.on_receive()`.
* `message_processing.process_message()` routes incoming text commands into the correct handler in `command_handlers.py` or `js8call_integration.py`.
* `command_handlers.py` implements menu navigation, mail, bulletins, utilities, games, readiness, and channel directory logic.
* `db_operations.py` provides the SQLite CRUD layer for bulletins, mail, readiness data, and games.
* `utils.py` centralizes user state tracking and message sending/syncing helpers.

---

## `server.py`

### `display_banner()`
Prints the TC²-BBS ASCII banner at startup. Call before initializing the server if you want the banner output.

### `main()`
Bootstraps the server. Typical entry point (invoked by `python server.py`). It:
1) Parses CLI args, 2) loads config, 3) opens the Meshtastic interface, 4) initializes the database, 5) subscribes to MQTT, and 6) starts JS8Call integration when configured.

---

## `config_init.py`

### `init_cli_parser() -> argparse.Namespace`
Builds and parses CLI arguments. Call at startup to retrieve parsed arguments such as `--config`, `--interface-type`, `--port`, and `--host`.

### `merge_config(system_config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]`
Merges CLI overrides into the config dict produced by `initialize_config()`. Call after `initialize_config()` and before opening an interface.

### `initialize_config(config_file: str | None = None) -> dict[str, Any]`
Reads `config.ini` (or another path) and returns a configuration dictionary with interface info, sync peers, and allow list. Call at startup to load config.

### `get_interface(system_config: dict[str, Any]) -> meshtastic.stream_interface.StreamInterface`
Creates a Meshtastic interface (serial or TCP) based on configuration. Call during startup and reuse the returned interface for messaging.

---

## `utils.py`

### `update_user_state(user_id, state)`
Stores per-user state in memory. Call after menus/steps change, typically from handlers.

### `get_user_state(user_id)`
Returns stored state for a user. `None` if no state exists. Called by `message_processing.process_message()`.

### `send_message(message, destination, interface)`
Splits a message into 200-byte chunks and sends via Meshtastic. Use for any outbound response to a user or broadcast.

### `get_node_info(interface, short_name)`
Returns a list of nodes matching a short name (case-insensitive). Useful for resolving recipients by short name.

### `get_node_id_from_num(node_num, interface)`
Maps a numeric node id (`node['num']`) to a Meshtastic node id.

### `get_node_short_name(node_id, interface)`
Returns `shortName` for a node id or `None` if not found.

### `send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface)`
Broadcasts a bulletin sync message to other BBS nodes. Called when a new bulletin is created.

### `send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes, interface)`
Broadcasts a mail sync message to other BBS nodes. Called when new mail is created.

### `send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface)`
Broadcasts a bulletin deletion to other BBS nodes.

### `send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface)`
Broadcasts a mail deletion to other BBS nodes.

### `send_channel_to_bbs_nodes(name, url, bbs_nodes, interface)`
Broadcasts a new channel entry to other BBS nodes.

---

## `message_processing.py`

### `process_message(sender_id, message, interface, is_sync_message=False)`
Routes incoming text to the proper handler based on state and command prefixes. Use it for all inbound text. It:
* Handles sync messages (`BULLETIN|`, `MAIL|`, `DELETE_*|`, `CHANNEL|`) by updating the DB.
* Handles quick commands like `sm,,`, `ttt,,`, `hang,,`, `c4,,`, `mm,,`, `bsset,,`, `bsfire,,`, `wc,,`, `triv,,`, `move,,`, `cm`, `pb,,`, `cb,,`, `chp,,`, and `chl`.
* Uses stored user state to process multi-step flows.

### `on_receive(packet, interface)`
Meshtastic callback for received packets. Decodes text payloads and delegates to `process_message()` if the packet is for this node or is a BBS sync message.

### `get_recipient_id_by_mail(unique_id)`
Looks up the recipient id for a mail record by unique id. Used when processing delete sync messages.

---

## `db_operations.py`

### Database setup

#### `get_db_connection()`
Returns a thread-local SQLite connection to `bulletins.db`.

#### `initialize_database()`
Creates all required tables if they do not exist. Call once at server startup.

### Channel directory

#### `add_channel(name, url, bbs_nodes=None, interface=None)`
Inserts a channel into the DB and optionally syncs to other BBS nodes.

#### `get_channels()`
Returns all channel entries (`name`, `url`).

### Bulletins

#### `add_bulletin(board, sender_short_name, subject, content, bbs_nodes, interface, unique_id=None)`
Creates a bulletin. Returns the bulletin `unique_id` and optionally syncs to other BBS nodes.

#### `get_bulletins(board)`
Returns bulletins for a board (`id`, `subject`, `sender_short_name`, `date`, `unique_id`).

#### `get_bulletin_content(bulletin_id)`
Returns full bulletin content and metadata for a given id.

#### `delete_bulletin(bulletin_id, bbs_nodes, interface)`
Deletes a bulletin and sends delete sync to other BBS nodes.

### Mail

#### `add_mail(sender_id, sender_short_name, recipient_id, subject, content, bbs_nodes, interface, unique_id=None)`
Creates mail. Returns the mail `unique_id` and optionally syncs to other BBS nodes.

#### `get_mail(recipient_id)`
Returns mail list for a recipient (`id`, `sender_short_name`, `subject`, `date`, `unique_id`).

#### `get_mail_content(mail_id, recipient_id)`
Returns mail content for a recipient. Caller should ensure the recipient matches.

#### `delete_mail(unique_id, recipient_id, bbs_nodes, interface)`
Deletes mail by unique id and sends delete sync to other BBS nodes.

#### `get_sender_id_by_mail_id(mail_id)`
Returns the sender id for a given mail id.

### Readiness roster & check-ins

#### `add_or_update_roster_entry(short_name, node_id, role, last_seen=None)`
Creates or updates a readiness roster entry.

#### `update_roster_last_seen(short_name, last_seen)`
Updates the `last_seen` field for a roster entry.

#### `delete_roster_entry(short_name)`
Deletes a roster entry and returns the row count deleted.

#### `get_roster_entries()`
Returns all roster entries (`short_name`, `node_id`, `role`, `last_seen`).

#### `add_checkin(short_name, node_id, status, note, timestamp)`
Adds a check-in record.

#### `get_latest_checkins()`
Returns the latest check-in per short name (ordered by timestamp).

### Game records

#### `create_tictactoe_game(player_x, player_o)` / `get_tictactoe_game(game_id)` / `update_tictactoe_game(game_id, board, next_turn, status, winner)`
Creates, fetches, and updates tic-tac-toe games.

#### `create_hangman_game(player_setter, player_guesser, secret_word)` / `get_hangman_game(game_id)` / `update_hangman_game(game_id, guessed_letters, attempts_left, status)`
Creates, fetches, and updates hangman games.

#### `create_connect4_game(player_r, player_y)` / `get_connect4_game(game_id)` / `update_connect4_game(game_id, board, next_turn, status, winner)`
Creates, fetches, and updates connect-four games.

#### `create_mastermind_game(player_setter, player_guesser, secret_code)` / `get_mastermind_game(game_id)` / `update_mastermind_game(game_id, guesses, status, last_feedback)`
Creates, fetches, and updates mastermind games.

#### `create_battleship_game(player1, player2, p1_ships)` / `get_battleship_game(game_id)` / `update_battleship_game(game_id, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status)`
Creates, fetches, and updates battleship games.

#### `create_word_chain_game(player1, player2, start_word)` / `get_word_chain_game(game_id)` / `update_word_chain_game(game_id, current_word, used_words, next_turn, status)`
Creates, fetches, and updates word-chain games.

#### `create_trivia_game(player1, player2, question, answer)` / `get_trivia_game(game_id)` / `update_trivia_game(game_id, p1_response, p2_response, status)`
Creates, fetches, and updates trivia games.

#### `create_boardgame_match(game_type, player1, player2)` / `get_boardgame_match(game_id)` / `update_boardgame_match(game_id, moves, next_turn, status)`
Creates, fetches, and updates generic board game matches.

---

## `command_handlers.py`

### Menu helpers

#### `build_menu(items, menu_name)`
Returns a formatted menu string for a list of menu tokens (`Q`, `B`, `U`, etc.). Used by help/menu handlers.

#### `handle_help_command(sender_id, interface, menu_name=None)`
Sends main or submenu help text to a user and updates menu state.

#### `get_node_name(node_id, interface)`
Returns a node's long name, or `Node <id>` if not found.

### Mail & bulletin entry points

#### `handle_mail_command(sender_id, interface)`
Sends the mail menu and sets state to `MAIL`.

#### `handle_bulletin_command(sender_id, interface)`
Sends bulletin menu and sets state to `BULLETIN_MENU`.

#### `handle_exit_command(sender_id, interface)`
Sends an exit/back response and resets state.

### Utilities entry points

#### `handle_stats_command(sender_id, interface)`
Starts the statistics flow.

#### `handle_fortune_command(sender_id, interface)`
Sends a random fortune from `fortunes.txt`.

#### `handle_wall_of_shame_command(sender_id, interface)`
Sends a list of recent offenders from `fail2ban` logs (if available).

#### `handle_time_command(sender_id, interface, menu_name=None)`
Sends current server time (and optionally returns to a menu).

#### `handle_sunmoon_command(sender_id, interface, menu_name=None)`
Sends sunrise/sunset (requires location config).

#### `handle_dictionary_command(sender_id, interface)` / `handle_dictionary_steps(sender_id, message, step, state, interface)`
Starts and handles the dictionary lookup flow (uses `Tools/dictionary.json`).

#### `handle_adsb_command(sender_id, interface)` / `handle_adsb_steps(sender_id, message, step, state, interface)`
Starts and handles ADS-B log parsing (calls `Tools/ADSBPArser.py`).

#### `handle_ollama_command(sender_id, interface)` / `handle_ollama_steps(sender_id, message, step, state, interface)`
Starts and handles Ollama LLM prompts (calls `Tools/Ollama.py`).

#### `handle_wx_command(sender_id, interface)` / `handle_wx_steps(sender_id, message, step, state, interface)`
Starts and handles weather history lookup (calls `Tools/wxparser.py`).

### Readiness features

#### `handle_readiness_checkin_command(sender_id, interface)`
Starts a readiness check-in flow.

#### `handle_readiness_roster_command(sender_id, interface)`
Starts the readiness roster flow.

#### `handle_go_bag_command(sender_id, interface)`
Sends the go-bag checklist.

#### `handle_radio_reference_command(sender_id, interface)`
Sends the radio/comms quick reference.

#### `_format_last_seen(timestamp)`
Formats a roster `last_seen` timestamp into a readable label.

#### `_send_mail_to_short_name(sender_id, interface, bbs_nodes, short_name, subject, content)`
Looks up a node by short name and sends mail to that node.

#### `_resolve_roster_node_id(node_id, interface)`
Attempts to resolve a roster node id to a short name.

#### `handle_checkin_steps(sender_id, message, step, state, interface, bbs_nodes)`
Implements readiness check-in step-by-step flow.

#### `handle_roster_steps(sender_id, message, step, state, interface)`
Implements roster step-by-step flow.

### Bulletin flow

#### `handle_bb_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step bulletin board flow for choosing board, reading posts, and posting new bulletins.

#### `handle_check_bulletin_command(sender_id, message, interface)`
Quick command handler for listing bulletins (`cb,,`).

#### `handle_read_bulletin_command(sender_id, message, state, interface)`
Reads a specific bulletin by id.

#### `handle_post_bulletin_command(sender_id, message, interface, bbs_nodes)`
Quick command handler for posting bulletins (`pb,,`).

### Mail flow

#### `handle_mail_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step mail flow for reading, sending, and deleting mail.

#### `handle_send_mail_command(sender_id, message, interface, bbs_nodes)`
Quick command handler for sending mail (`sm,,`).

#### `handle_check_mail_command(sender_id, interface)`
Quick command handler for listing mail (`cm`).

#### `handle_read_mail_command(sender_id, message, state, interface)`
Reads a specific mail message by id.

#### `handle_delete_mail_confirmation(sender_id, message, state, interface, bbs_nodes)`
Confirms and deletes mail by unique id.

### Channel directory flow

#### `handle_channel_directory_command(sender_id, interface)`
Sends the channel directory menu and sets state.

#### `handle_channel_directory_steps(sender_id, message, step, state, interface)`
Multi-step handler for reading/adding channels.

#### `handle_post_channel_command(sender_id, message, interface)`
Quick command for posting a channel (`chp,,`).

#### `handle_check_channel_command(sender_id, interface)`
Quick command for listing channels (`ch` menu flow).

#### `handle_read_channel_command(sender_id, message, state, interface)`
Reads a channel entry by id.

#### `handle_list_channels_command(sender_id, interface)`
Quick command for listing channels (`chl`).

### Stats flow

#### `handle_stats_steps(sender_id, message, step, interface)`
Multi-step handler for requesting stats (switches between node stats and general stats output).

### Game: Tic-Tac-Toe

#### `format_tictactoe_board(board)`
Formats a 9-char board string into a 3x3 grid.

#### `check_tictactoe_winner(board)`
Returns the winner symbol (`X` or `O`) or `None`.

#### `send_tictactoe_status(recipient_id, interface, game_id, board, next_turn, status, winner)`
Sends the current game state to a player.

#### `create_tictactoe_game_for_players(sender_id, opponent_id, interface, bbs_nodes)`
Creates a new game in the DB and notifies players.

#### `handle_tictactoe_command(sender_id, interface)`
Starts a tic-tac-toe challenge flow.

#### `handle_tictactoe_move(sender_id, game_id, move, interface)`
Validates a move and updates the game.

#### `handle_tictactoe_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step flow for challenge setup and gameplay.

#### `handle_tictactoe_move_command(sender_id, message, interface)`
Quick command handler for moves (`ttt,,<game_id>,<pos>`).

### Game: Hangman

#### `format_hangman_word(secret_word, guessed_letters)`
Returns a masked word using guessed letters.

#### `send_hangman_status(recipient_id, interface, game_id, secret_word, guessed_letters, attempts_left, status)`
Sends the current game state to a player.

#### `create_hangman_game_for_players(sender_id, opponent_id, secret_word, interface, bbs_nodes)`
Creates a hangman game and notifies players.

#### `handle_hangman_command(sender_id, interface)`
Starts hangman setup flow.

#### `handle_hangman_guess(sender_id, game_id, guess, interface)`
Validates a guess and updates the game.

#### `handle_hangman_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step flow for setting the word and guessing.

#### `handle_hangman_guess_command(sender_id, message, interface)`
Quick command handler for guesses (`hang,,<game_id>,<letter>`).

### Game: Connect Four

#### `format_connect4_board(board)`
Formats the 42-char board into a 6x7 grid.

#### `check_connect4_winner(board)`
Returns the winner symbol (`R`/`Y`) or `None`.

#### `send_connect4_status(recipient_id, interface, game_id, board, next_turn, status, winner)`
Sends the current game state to a player.

#### `create_connect4_game_for_players(sender_id, opponent_id, interface, bbs_nodes)`
Creates a connect-four game and notifies players.

#### `handle_connect4_command(sender_id, interface)`
Starts connect-four setup.

#### `handle_connect4_move(sender_id, game_id, move, interface)`
Validates a move and updates the game.

#### `handle_connect4_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step flow for setup and gameplay.

#### `handle_connect4_move_command(sender_id, message, interface)`
Quick command handler for moves (`c4,,<game_id>,<column>`).

### Game: Mastermind

#### `mastermind_feedback(secret_code, guess)`
Returns feedback counts for a mastermind guess.

#### `send_mastermind_status(recipient_id, interface, game_id, guesses, last_feedback, status)`
Sends the current game state to a player.

#### `create_mastermind_game_for_players(sender_id, opponent_id, secret_code, interface, bbs_nodes)`
Creates a mastermind game and notifies players.

#### `handle_mastermind_command(sender_id, interface)`
Starts mastermind setup.

#### `handle_mastermind_guess(sender_id, game_id, guess, interface)`
Validates a guess and updates the game.

#### `handle_mastermind_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step flow for setup and gameplay.

#### `handle_mastermind_guess_command(sender_id, message, interface)`
Quick command handler for guesses (`mm,,<game_id>,<code>`).

### Game: Battleship (Lite)

#### `parse_battleship_positions(raw_positions)`
Parses positions text (e.g., `A1,A2`) into an internal list.

#### `send_battleship_status(recipient_id, interface, game_id, p1_hits, p2_hits, next_turn, status, is_player1)`
Sends current battleship status to a player.

#### `create_battleship_game_for_players(sender_id, opponent_id, positions, interface, bbs_nodes)`
Creates a battleship game and notifies players.

#### `handle_battleship_command(sender_id, interface)`
Starts battleship setup.

#### `handle_battleship_set_ships(sender_id, game_id, positions, interface)`
Validates ship placement and updates the game.

#### `handle_battleship_fire(sender_id, game_id, target, interface)`
Validates a fire command and updates hits.

#### `handle_battleship_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step setup and gameplay handler.

#### `handle_battleship_set_command(sender_id, message, interface)`
Quick command handler for placement (`bsset,,<game_id>,<positions>`).

#### `handle_battleship_fire_command(sender_id, message, interface)`
Quick command handler for fire (`bsfire,,<game_id>,<target>`).

### Game: Word Chain

#### `send_word_chain_status(recipient_id, interface, game_id, current_word, used_words, next_turn, status, is_player1)`
Sends current word-chain status.

#### `create_word_chain_game_for_players(sender_id, opponent_id, start_word, interface, bbs_nodes)`
Creates a word-chain game and notifies players.

#### `handle_word_chain_command(sender_id, interface)`
Starts word-chain setup.

#### `handle_word_chain_play(sender_id, game_id, word, interface)`
Validates a play and updates the game.

#### `handle_word_chain_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step setup and gameplay handler.

#### `handle_word_chain_play_command(sender_id, message, interface)`
Quick command handler for plays (`wc,,<game_id>,<word>`).

### Game: Trivia

#### `send_trivia_status(recipient_id, interface, game_id, question, status, p1_response, p2_response, is_player1)`
Sends current trivia status.

#### `create_trivia_game_for_players(sender_id, opponent_id, question, answer, interface, bbs_nodes)`
Creates a trivia game and notifies players.

#### `handle_trivia_command(sender_id, interface)`
Starts trivia setup.

#### `handle_trivia_answer(sender_id, game_id, answer, interface)`
Validates and stores trivia answers.

#### `handle_trivia_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step setup and gameplay handler.

#### `handle_trivia_answer_command(sender_id, message, interface)`
Quick command handler (`triv,,<game_id>,<answer>`).

### Game: Chess/Checkers (generic boardgame)

#### `send_boardgame_status(recipient_id, interface, game_id, game_type, moves, next_turn, status, is_player1)`
Sends current boardgame status.

#### `create_boardgame_match_for_players(sender_id, opponent_id, game_type, interface, bbs_nodes)`
Creates a boardgame match and notifies players.

#### `handle_boardgame_command(sender_id, interface)`
Starts boardgame setup.

#### `handle_boardgame_move(sender_id, game_id, move, interface)`
Validates a move and updates the game.

#### `handle_boardgame_steps(sender_id, message, step, state, interface, bbs_nodes)`
Multi-step setup and gameplay handler.

#### `handle_boardgame_move_command(sender_id, message, interface)`
Quick command handler (`move,,<game_id>,<move>`).

---

## `js8call_integration.py`

### `from_message(content)`
Parses a JSON string from JS8Call into a dictionary.

### `to_message(typ, value='', params=None)`
Builds the JSON payload for JS8Call commands.

### `JS8CallClient` class

#### `__init__(self, interface, logger=None)`
Creates the client, reads configuration, and prepares DB tables if configured.

#### `create_tables(self)`
Creates JS8Call message tables when a DB is configured.

#### `insert_message(self, sender, receiver, message)`
Stores a direct message in the JS8Call DB.

#### `insert_group(self, sender, groupname, message)`
Stores a group message.

#### `insert_urgent(self, sender, groupname, message)`
Stores an urgent group message and triggers a notification.

#### `process(self, message)`
Handles JS8Call RX messages and dispatches to storage or notification.

#### `send(self, *args, **kwargs)`
Sends a JSON command to JS8Call over the socket.

#### `connect(self)`
Connects to the JS8Call TCP server and starts processing incoming messages.

#### `close(self)`
Closes the connection loop.

### JS8Call menu handlers

#### `handle_js8call_command(sender_id, interface)`
Sends the JS8Call menu and sets state.

#### `handle_js8call_steps(sender_id, message, step, interface, state)`
Routes JS8Call menu selections.

#### `handle_group_messages_command(sender_id, interface)`
Lists available JS8Call groups and sets state for selection.

#### `handle_station_messages_command(sender_id, interface)`
Lists JS8Call station messages and returns to the JS8Call menu.

#### `handle_urgent_messages_command(sender_id, interface)`
Lists JS8Call urgent messages and returns to the JS8Call menu.

#### `handle_group_message_selection(sender_id, message, step, state, interface)`
Shows messages for a selected group.

---

## `db_admin.py`

### `get_db_connection()`
Returns a thread-local SQLite connection to `bulletins.db`.

### `initialize_database()`
Creates bulletin/mail/channel tables (admin tool only).

### `list_bulletins()` / `list_mail()` / `list_channels()`
Prints records to the console for admin review.

### `delete_bulletin()` / `delete_mail()` / `delete_channel()`
Deletes selected records by id from the admin CLI.

### `display_menu()` / `display_banner()` / `clear_screen()`
CLI display helpers for the admin console.

### `input_bold(prompt)` / `print_bold(message)` / `print_separator()`
Console formatting helpers used by the admin CLI.

### `main()`
Runs the interactive admin CLI menu.

---

## Tooling scripts

### `Tools/ADSBPArser.py`

#### `get_docker_logs(container_name="readsb3")`
Reads docker logs for an ADS-B container and returns log lines.

#### `parse_block(block)`
Parses a single ADS-B block of log lines into a plane dictionary.

#### `parse_planes_from_lines(lines)`
Parses all planes from log lines and returns a list of plane dicts.

#### `get_last_unique_planes(planes, max_planes=10)`
Returns the most recent unique planes by ICAO.

#### `haversine(lat1, lon1, lat2, lon2)`
Computes distance in miles between two coordinates.

#### `main()`
CLI entry point: parse logs and print latest, last10, or alert data.

### `Tools/Ollama.py`

#### `ask_ollama(prompt)`
Calls the Ollama HTTP API and returns the model response string.

#### `main()`
CLI entry point: takes a prompt and prints the model response.

### `Tools/wxparser.py`

#### `fetch_weather_history()`
Calls the local weather API and returns JSON history.

#### `show_entries(entries, last_n=5)`
Prints the last `n` weather entries.

#### `main()`
CLI entry point: reads how many entries to show and prints them.

### `Tools/docker/weatherstac/api/api.py`

#### `latest()`
FastAPI route returning the latest weather entry.

#### `history(limit: int = 50)`
FastAPI route returning a list of recent entries.

#### `ws(ws: WebSocket)`
WebSocket endpoint that streams new weather messages.

#### `dashboard()`
FastAPI route serving a basic HTML dashboard.
