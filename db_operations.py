import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime

from meshtastic import BROADCAST_NUM

from utils import (
    send_bulletin_to_bbs_nodes,
    send_delete_bulletin_to_bbs_nodes,
    send_delete_mail_to_bbs_nodes,
    send_mail_to_bbs_nodes, send_message, send_channel_to_bbs_nodes
)


DB_FILE = "bulletins.db"
thread_local = threading.local()

def get_db_connection():
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect(DB_FILE)
    return thread_local.connection

def close_db_connection():
    conn = getattr(thread_local, 'connection', None)
    if conn:
        conn.close()
        delattr(thread_local, 'connection')

def clear_database():
    close_db_connection()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        logging.info("Database file removed.")
    else:
        logging.info("Database file not found; nothing to remove.")

def get_database_size_bytes():
    if not os.path.exists(DB_FILE):
        return 0
    return os.path.getsize(DB_FILE)

def initialize_database():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bulletins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board TEXT NOT NULL,
                    sender_short_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    unique_id TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS mail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    sender_short_name TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    unique_id TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS tictactoe_games (
                    game_id TEXT PRIMARY KEY,
                    player_x TEXT NOT NULL,
                    player_o TEXT NOT NULL,
                    board TEXT NOT NULL,
                    next_turn TEXT NOT NULL,
                    status TEXT NOT NULL,
                    winner TEXT,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS hangman_games (
                    game_id TEXT PRIMARY KEY,
                    player_setter TEXT NOT NULL,
                    player_guesser TEXT NOT NULL,
                    secret_word TEXT NOT NULL,
                    guessed_letters TEXT NOT NULL,
                    attempts_left INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS connect4_games (
                    game_id TEXT PRIMARY KEY,
                    player_r TEXT NOT NULL,
                    player_y TEXT NOT NULL,
                    board TEXT NOT NULL,
                    next_turn TEXT NOT NULL,
                    status TEXT NOT NULL,
                    winner TEXT,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS mastermind_games (
                    game_id TEXT PRIMARY KEY,
                    player_setter TEXT NOT NULL,
                    player_guesser TEXT NOT NULL,
                    secret_code TEXT NOT NULL,
                    guesses TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_feedback TEXT,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS battleship_games (
                    game_id TEXT PRIMARY KEY,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    p1_ships TEXT,
                    p2_ships TEXT,
                    p1_hits TEXT NOT NULL,
                    p2_hits TEXT NOT NULL,
                    next_turn TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS word_chain_games (
                    game_id TEXT PRIMARY KEY,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    current_word TEXT NOT NULL,
                    used_words TEXT NOT NULL,
                    next_turn TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS trivia_games (
                    game_id TEXT PRIMARY KEY,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    p1_response TEXT,
                    p2_response TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS boardgame_matches (
                    game_id TEXT PRIMARY KEY,
                    game_type TEXT NOT NULL,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    moves TEXT NOT NULL,
                    next_turn TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS readiness_roster (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    short_name TEXT NOT NULL UNIQUE,
                    node_id TEXT,
                    role TEXT,
                    last_seen TEXT
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS readiness_checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    short_name TEXT NOT NULL,
                    node_id TEXT,
                    status TEXT NOT NULL,
                    note TEXT,
                    timestamp TEXT NOT NULL
                );''')
    conn.commit()
    print("Database schema initialized.")

def add_channel(name, url, bbs_nodes=None, interface=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO channels (name, url) VALUES (?, ?)", (name, url))
    conn.commit()

    if bbs_nodes and interface:
        send_channel_to_bbs_nodes(name, url, bbs_nodes, interface)


def get_channels():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, url FROM channels")
    return c.fetchall()



def add_bulletin(board, sender_short_name, subject, content, bbs_nodes, interface, unique_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d %H:%M')
    if not unique_id:
        unique_id = str(uuid.uuid4())
    c.execute(
        "INSERT INTO bulletins (board, sender_short_name, date, subject, content, unique_id) VALUES (?, ?, ?, ?, ?, ?)",
        (board, sender_short_name, date, subject, content, unique_id))
    conn.commit()
    if bbs_nodes and interface:
        send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface)

    # New logic to send group chat notification for urgent bulletins
    if board.lower() == "urgent":
        notification_message = f"💥NEW URGENT BULLETIN💥\nFrom: {sender_short_name}\nTitle: {subject}"
        send_message(notification_message, BROADCAST_NUM, interface)

    return unique_id


def get_bulletins(board):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, subject, sender_short_name, date, unique_id FROM bulletins WHERE board = ?", (board,))
    return c.fetchall()

def get_bulletin_content(bulletin_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender_short_name, date, subject, content, unique_id FROM bulletins WHERE id = ?", (bulletin_id,))
    return c.fetchone()


def delete_bulletin(bulletin_id, bbs_nodes, interface):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM bulletins WHERE id = ?", (bulletin_id,))
    conn.commit()
    send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface)

def add_mail(sender_id, sender_short_name, recipient_id, subject, content, bbs_nodes, interface, unique_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d %H:%M')
    if not unique_id:
        unique_id = str(uuid.uuid4())
    c.execute("INSERT INTO mail (sender, sender_short_name, recipient, date, subject, content, unique_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (sender_id, sender_short_name, recipient_id, date, subject, content, unique_id))
    conn.commit()
    if bbs_nodes and interface:
        send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes, interface)
    return unique_id


def add_or_update_roster_entry(short_name, node_id, role, last_seen=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, last_seen FROM readiness_roster WHERE short_name = ?", (short_name,))
    existing = c.fetchone()
    if existing:
        current_last_seen = existing[1]
        updated_last_seen = last_seen if last_seen else current_last_seen
        c.execute(
            "UPDATE readiness_roster SET node_id = ?, role = ?, last_seen = ? WHERE short_name = ?",
            (node_id, role, updated_last_seen, short_name)
        )
    else:
        c.execute(
            "INSERT INTO readiness_roster (short_name, node_id, role, last_seen) VALUES (?, ?, ?, ?)",
            (short_name, node_id, role, last_seen)
        )
    conn.commit()


def update_roster_last_seen(short_name, last_seen):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE readiness_roster SET last_seen = ? WHERE short_name = ?", (last_seen, short_name))
    conn.commit()


def delete_roster_entry(short_name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM readiness_roster WHERE short_name = ?", (short_name,))
    conn.commit()
    return c.rowcount


def get_roster_entries():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT short_name, node_id, role, last_seen FROM readiness_roster ORDER BY short_name")
    return c.fetchall()


def add_checkin(short_name, node_id, status, note, timestamp):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO readiness_checkins (short_name, node_id, status, note, timestamp) VALUES (?, ?, ?, ?, ?)",
        (short_name, node_id, status, note, timestamp)
    )
    conn.commit()


def get_latest_checkins():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT c.short_name, c.status, c.note, c.timestamp
                 FROM readiness_checkins c
                 JOIN (
                     SELECT short_name, MAX(timestamp) AS max_ts
                     FROM readiness_checkins
                     GROUP BY short_name
                 ) latest
                 ON c.short_name = latest.short_name AND c.timestamp = latest.max_ts
                 ORDER BY c.timestamp DESC''')
    return c.fetchall()

def get_mail(recipient_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, sender_short_name, subject, date, unique_id FROM mail WHERE recipient = ?", (recipient_id,))
    return c.fetchall()

def get_mail_content(mail_id, recipient_id):
    # TODO: ensure only recipient can read mail
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender_short_name, date, subject, content, unique_id FROM mail WHERE id = ? and recipient = ?", (mail_id, recipient_id,))
    return c.fetchone()

def delete_mail(unique_id, recipient_id, bbs_nodes, interface):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT recipient FROM mail WHERE unique_id = ?", (unique_id,))
        result = c.fetchone()
        if result is None:
            logging.error(f"No mail found with unique_id: {unique_id}")
            return  # Early exit if no matching mail found
        recipient_id = result[0]
        logging.info(f"Attempting to delete mail with unique_id: {unique_id} by {recipient_id}")
        c.execute("DELETE FROM mail WHERE unique_id = ? and recipient = ?", (unique_id, recipient_id,))
        conn.commit()
        send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface)
        logging.info(f"Mail with unique_id: {unique_id} deleted and sync message sent.")
    except Exception as e:
        logging.error(f"Error deleting mail with unique_id {unique_id}: {e}")
        raise


def get_sender_id_by_mail_id(mail_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender FROM mail WHERE id = ?", (mail_id,))
    result = c.fetchone()
    if result:
        return result[0]
    return None


def create_tictactoe_game(player_x, player_o):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    board = "---------"
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO tictactoe_games (game_id, player_x, player_o, board, next_turn, status, winner, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player_x, player_o, board, "X", "active", None, created_at)
    )
    conn.commit()
    return game_id


def get_tictactoe_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player_x, player_o, board, next_turn, status, winner "
        "FROM tictactoe_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_tictactoe_game(game_id, board, next_turn, status, winner):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE tictactoe_games SET board = ?, next_turn = ?, status = ?, winner = ? WHERE game_id = ?",
        (board, next_turn, status, winner, game_id)
    )
    conn.commit()


def create_hangman_game(player_setter, player_guesser, secret_word):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO hangman_games (game_id, player_setter, player_guesser, secret_word, guessed_letters, attempts_left, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player_setter, player_guesser, secret_word, "", 6, "active", created_at)
    )
    conn.commit()
    return game_id


def get_hangman_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player_setter, player_guesser, secret_word, guessed_letters, attempts_left, status "
        "FROM hangman_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_hangman_game(game_id, guessed_letters, attempts_left, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE hangman_games SET guessed_letters = ?, attempts_left = ?, status = ? WHERE game_id = ?",
        (guessed_letters, attempts_left, status, game_id)
    )
    conn.commit()


def create_connect4_game(player_r, player_y):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    board = "-" * 42
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO connect4_games (game_id, player_r, player_y, board, next_turn, status, winner, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player_r, player_y, board, "R", "active", None, created_at)
    )
    conn.commit()
    return game_id


def get_connect4_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player_r, player_y, board, next_turn, status, winner "
        "FROM connect4_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_connect4_game(game_id, board, next_turn, status, winner):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE connect4_games SET board = ?, next_turn = ?, status = ?, winner = ? WHERE game_id = ?",
        (board, next_turn, status, winner, game_id)
    )
    conn.commit()


def create_mastermind_game(player_setter, player_guesser, secret_code):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO mastermind_games (game_id, player_setter, player_guesser, secret_code, guesses, status, last_feedback, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player_setter, player_guesser, secret_code, "", "active", None, created_at)
    )
    conn.commit()
    return game_id


def get_mastermind_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player_setter, player_guesser, secret_code, guesses, status, last_feedback "
        "FROM mastermind_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_mastermind_game(game_id, guesses, status, last_feedback):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE mastermind_games SET guesses = ?, status = ?, last_feedback = ? WHERE game_id = ?",
        (guesses, status, last_feedback, game_id)
    )
    conn.commit()


def create_battleship_game(player1, player2, p1_ships):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO battleship_games (game_id, player1, player2, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player1, player2, p1_ships, None, "", "", "P1", "waiting_for_opponent", created_at)
    )
    conn.commit()
    return game_id


def get_battleship_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player1, player2, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status "
        "FROM battleship_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_battleship_game(game_id, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE battleship_games SET p1_ships = ?, p2_ships = ?, p1_hits = ?, p2_hits = ?, next_turn = ?, status = ? "
        "WHERE game_id = ?",
        (p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status, game_id)
    )
    conn.commit()


def create_word_chain_game(player1, player2, start_word):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO word_chain_games (game_id, player1, player2, current_word, used_words, next_turn, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player1, player2, start_word, start_word, "P2", "active", created_at)
    )
    conn.commit()
    return game_id


def get_word_chain_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player1, player2, current_word, used_words, next_turn, status "
        "FROM word_chain_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_word_chain_game(game_id, current_word, used_words, next_turn, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE word_chain_games SET current_word = ?, used_words = ?, next_turn = ?, status = ? WHERE game_id = ?",
        (current_word, used_words, next_turn, status, game_id)
    )
    conn.commit()


def create_trivia_game(player1, player2, question, answer):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO trivia_games (game_id, player1, player2, question, answer, p1_response, p2_response, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, player1, player2, question, answer, None, None, "active", created_at)
    )
    conn.commit()
    return game_id


def get_trivia_game(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, player1, player2, question, answer, p1_response, p2_response, status "
        "FROM trivia_games WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_trivia_game(game_id, p1_response, p2_response, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE trivia_games SET p1_response = ?, p2_response = ?, status = ? WHERE game_id = ?",
        (p1_response, p2_response, status, game_id)
    )
    conn.commit()


def create_boardgame_match(game_type, player1, player2):
    conn = get_db_connection()
    c = conn.cursor()
    game_id = str(uuid.uuid4())
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute(
        "INSERT INTO boardgame_matches (game_id, game_type, player1, player2, moves, next_turn, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, game_type, player1, player2, "", "P1", "active", created_at)
    )
    conn.commit()
    return game_id


def get_boardgame_match(game_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT game_id, game_type, player1, player2, moves, next_turn, status "
        "FROM boardgame_matches WHERE game_id = ?",
        (game_id,)
    )
    return c.fetchone()


def update_boardgame_match(game_id, moves, next_turn, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE boardgame_matches SET moves = ?, next_turn = ?, status = ? WHERE game_id = ?",
        (moves, next_turn, status, game_id)
    )
    conn.commit()
