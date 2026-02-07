import configparser
import datetime
import json
import logging
import os
import random
import subprocess
import time
from suntime import Sun, SunTimeException

from meshtastic import BROADCAST_NUM

from db_operations import (
    add_bulletin, add_mail, delete_mail,
    get_bulletin_content, get_bulletins,
    get_mail, get_mail_content,
    add_channel, get_channels, get_sender_id_by_mail_id,
    create_tictactoe_game, get_tictactoe_game, update_tictactoe_game,
    create_hangman_game, get_hangman_game, update_hangman_game,
    create_connect4_game, get_connect4_game, update_connect4_game,
    create_mastermind_game, get_mastermind_game, update_mastermind_game,
    create_battleship_game, get_battleship_game, update_battleship_game,
    create_word_chain_game, get_word_chain_game, update_word_chain_game,
    create_trivia_game, get_trivia_game, update_trivia_game,
    create_boardgame_match, get_boardgame_match, update_boardgame_match
)
from utils import (
    get_node_id_from_num, get_node_info,
    get_node_short_name, send_message,
    update_user_state
)
from Tools.Ollama import ask_ollama

# Read the configuration for menu options
config = configparser.ConfigParser()
config.read('config.ini')

main_menu_items = config['menu']['main_menu_items'].split(',')
bbs_menu_items = config['menu']['bbs_menu_items'].split(',')
utilities_menu_items = config['menu']['utilities_menu_items'].split(',')
games_menu_items = config['menu'].get('games_menu_items', 'T').split(',')

DICTIONARY_PATH = os.path.join('Tools', 'dictionary.json')
_dictionary_cache = None
ADSB_PARSER_PATH = os.path.join(os.path.dirname(__file__), 'Tools', 'ADSBPArser.py')
WX_PARSER_PATH = os.path.join(os.path.dirname(__file__), 'Tools', 'wxparser.py')


def build_menu(items, menu_name):
    menu_str = f"{menu_name}\n"
    for item in items:
        if item.strip() == 'Q':
            menu_str += "[Q]uick Commands\n"
        elif item.strip() == 'B':
            if menu_name == "💾TC² BBS💾":
                menu_str += "[B]BS\n"
            else:
                menu_str += "[B]ack\n"
        elif item.strip() == 'U':
            menu_str += "[U]tilities\n"
        elif item.strip() == 'G':
            menu_str += "[G]ames\n"
        elif item.strip() == 'X':
            menu_str += "E[X]IT\n"
        elif item.strip() == 'M':
            if "Games" in menu_name:
                menu_str += "[M]astermind\n"
            else:
                menu_str += "[M]ail\n"
        elif item.strip() == 'C':
            if "Games" in menu_name:
                menu_str += "[C]onnect Four\n"
            else:
                menu_str += "[C]hannel Dir\n"
        elif item.strip() == 'J':
            menu_str += "[J]S8CALL\n"
        elif item.strip() == 'S':
            menu_str += "[S]tats [1]\n"
        elif item.strip() == 'F':
            menu_str += "[F]ortune [2]\n"
        elif item.strip() == 'W':
            if "Games" in menu_name:
                menu_str += "[W]ord Chain\n"
            else:
                menu_str += "[W]all of Shame [3]\n"
        elif item.strip() == 'T':
            if "Games" in menu_name:
                menu_str += "[T]ic Tac Toe\n"
            else:
                menu_str += "[T]ime [4]\n"
        elif item.strip() == 'H':
            if "Games" in menu_name:
                menu_str += "[H]angman\n"
            else:
                menu_str += "Weat[H]er (WX) [9]\n"
        elif item.strip() == 'L':
            if "Games" in menu_name:
                menu_str += "[L]Battleship (Lite)\n"
        elif item.strip() == 'N':
            menu_str += "Su[N]Moon [5]\n"
        elif item.strip() == 'D':
            menu_str += "[D]efine [6]\n"
        elif item.strip() == 'A':
            menu_str += "[A]DSB [7]\n"
        elif item.strip() == 'O':
            menu_str += "[O]llama [8]\n"
        elif item.strip() == 'R':
            if "Games" in menu_name:
                menu_str += "T[R]ivia\n"
        elif item.strip() == 'K':
            if "Games" in menu_name:
                menu_str += "[K]Chess/Checkers\n"
    return menu_str


def handle_help_command(sender_id, interface, menu_name=None):
    if menu_name:
        update_user_state(sender_id, {'command': 'MENU', 'menu': menu_name, 'step': 1})
        if menu_name == 'bbs':
            response = build_menu(bbs_menu_items, "📰BBS Menu📰")
        elif menu_name == 'utilities':
            response = build_menu(utilities_menu_items, "🛠️Utilities Menu🛠️")
        elif menu_name == 'games':
            response = build_menu(games_menu_items, "🎮Games Menu🎮")
        response = f"{response}Type BACK to return."
    else:
        update_user_state(sender_id, {'command': 'MAIN_MENU', 'step': 1})  # Reset to main menu state
        response = build_menu(main_menu_items, "💾TC² BBS💾")
    send_message(response, sender_id, interface)


def get_node_name(node_id, interface):
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info['user']['longName']
    return f"Node {node_id}"


def handle_mail_command(sender_id, interface):
    response = "✉️Mail Menu✉️\nWhat would you like to do with mail?\n[R]ead  [S]end\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'MAIL', 'step': 1})



def handle_bulletin_command(sender_id, interface):
    response = "📰Bulletin Menu📰\nWhich board would you like to enter?\n[G]eneral  [I]nfo  [N]ews  [U]rgent\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'BULLETIN_MENU', 'step': 1})


def handle_exit_command(sender_id, interface):
    send_message("Type 'HELP' for a list of commands.", sender_id, interface)
    update_user_state(sender_id, None)


def handle_stats_command(sender_id, interface):
    response = "📊Stats Menu📊\nWhat stats would you like to view?\n[N]odes  [H]ardware  [R]oles\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'STATS', 'step': 1})


def handle_fortune_command(sender_id, interface):
    try:
        with open('fortunes.txt', 'r') as file:
            fortunes = file.readlines()
        if not fortunes:
            send_message("No fortunes available.", sender_id, interface)
            return
        fortune = random.choice(fortunes).strip()
        decorated_fortune = f"🔮 {fortune} 🔮"
        send_message(decorated_fortune, sender_id, interface)
    except Exception as e:
        send_message(f"Error generating fortune: {e}", sender_id, interface)


def handle_stats_steps(sender_id, message, step, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message
        if choice in {'b', 'back'}:
            handle_help_command(sender_id, interface, 'utilities')
            return
        if choice == 'x':
            handle_help_command(sender_id, interface)
            return
        elif choice == 'n':
            current_time = int(time.time())
            timeframes = {
                "All time": None,
                "Last 24 hours": 86400,
                "Last 8 hours": 28800,
                "Last hour": 3600
            }
            total_nodes_summary = []

            for period, seconds in timeframes.items():
                if seconds is None:
                    total_nodes = len(interface.nodes)
                else:
                    time_limit = current_time - seconds
                    total_nodes = sum(1 for node in interface.nodes.values() if node.get('lastHeard', 0) >= time_limit)
                total_nodes_summary.append(f"- {period}: {total_nodes}")

            response = "Total nodes seen:\n" + "\n".join(total_nodes_summary)
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)
        elif choice == 'h':
            hw_models = {}
            for node in interface.nodes.values():
                hw_model = node['user'].get('hwModel', 'Unknown')
                hw_models[hw_model] = hw_models.get(hw_model, 0) + 1
            response = "Hardware Models:\n" + "\n".join([f"{model}: {count}" for model, count in hw_models.items()])
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)
        elif choice == 'r':
            roles = {}
            for node in interface.nodes.values():
                role = node['user'].get('role', 'Unknown')
                roles[role] = roles.get(role, 0) + 1
            response = "Roles:\n" + "\n".join([f"{role}: {count}" for role, count in roles.items()])
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)


def handle_bb_steps(sender_id, message, step, state, interface, bbs_nodes):
    boards = {0: "General", 1: "Info", 2: "News", 3: "Urgent"}
    if step == 1:
        if message.lower() == 'e':
            handle_help_command(sender_id, interface, 'bbs')
            return
        board_name = boards[int(message)]
        response = f"What would you like to do in the {board_name} board?\n[R]ead  [P]ost"
        send_message(response, sender_id, interface)
        update_user_state(sender_id, {'command': 'BULLETIN_ACTION', 'step': 2, 'board': board_name})

    elif step == 2:
        board_name = state['board']
        if message.lower() == 'r':
            bulletins = get_bulletins(board_name)
            if bulletins:
                send_message(f"Select a bulletin number to view from {board_name}:", sender_id, interface)
                for bulletin in bulletins:
                    send_message(f"[{bulletin[0]}] {bulletin[1]}", sender_id, interface)
                update_user_state(sender_id, {'command': 'BULLETIN_READ', 'step': 3, 'board': board_name})
            else:
                send_message(f"No bulletins in {board_name}.", sender_id, interface)
                handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)
        elif message.lower() == 'p':
            if board_name.lower() == 'urgent':
                node_id = get_node_id_from_num(sender_id, interface)
                allowed_nodes = interface.allowed_nodes
                print(f"Checking permissions for node_id: {node_id} with allowed_nodes: {allowed_nodes}")  # Debug statement
                if allowed_nodes and node_id not in allowed_nodes:
                    send_message("You don't have permission to post to this board.", sender_id, interface)
                    handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)
                    return
            send_message("What is the subject of your bulletin? Keep it short.", sender_id, interface)
            update_user_state(sender_id, {'command': 'BULLETIN_POST', 'step': 4, 'board': board_name})

    elif step == 3:
        bulletin_id = int(message)
        sender_short_name, date, subject, content, unique_id = get_bulletin_content(bulletin_id)
        send_message(f"From: {sender_short_name}\nDate: {date}\nSubject: {subject}\n- - - - - - -\n{content}", sender_id, interface)
        board_name = state['board']
        handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)

    elif step == 4:
        subject = message
        send_message("Send the contents of your bulletin. Send a message with END when finished.", sender_id, interface)
        update_user_state(sender_id, {'command': 'BULLETIN_POST_CONTENT', 'step': 5, 'board': state['board'], 'subject': subject, 'content': ''})

    elif step == 5:
        if message.lower() == "end":
            board = state['board']
            subject = state['subject']
            content = state['content']
            node_id = get_node_id_from_num(sender_id, interface)
            node_info = interface.nodes.get(node_id)
            if node_info is None:
                send_message("Error: Unable to retrieve your node information.", sender_id, interface)
                update_user_state(sender_id, None)
                return
            sender_short_name = node_info['user'].get('shortName', f"Node {sender_id}")
            unique_id = add_bulletin(board, sender_short_name, subject, content, bbs_nodes, interface)
            send_message(f"Your bulletin '{subject}' has been posted to {board}.\n(╯°□°)╯📄📌[{board}]", sender_id, interface)
            handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)
        else:
            state['content'] += message + "\n"
            update_user_state(sender_id, state)



def handle_mail_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message
        if choice in {'b', 'back'}:
            handle_help_command(sender_id, interface, 'bbs')
            return
        if choice == 'r':
            sender_node_id = get_node_id_from_num(sender_id, interface)
            mail = get_mail(sender_node_id)
            if mail:
                send_message(f"You have {len(mail)} mail messages. Select a message number to read:", sender_id, interface)
                for msg in mail:
                    send_message(f"-{msg[0]}-\nDate: {msg[3]}\nFrom: {msg[1]}\nSubject: {msg[2]}", sender_id, interface)
                update_user_state(sender_id, {'command': 'MAIL', 'step': 2})
            else:
                send_message("There are no messages in your mailbox.📭", sender_id, interface)
                update_user_state(sender_id, None)
        elif choice == 's':
            send_message("What is the Short Name of the node you want to leave a message for?", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 3})
        elif choice == 'x':
            handle_help_command(sender_id, interface)

    elif step == 2:
        mail_id = int(message)
        try:
            sender_node_id = get_node_id_from_num(sender_id, interface)
            sender, date, subject, content, unique_id = get_mail_content(mail_id, sender_node_id)
            send_message(f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n{content}", sender_id, interface)
            send_message("What would you like to do with this message?\n[K]eep  [D]elete  [R]eply", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 4, 'mail_id': mail_id, 'unique_id': unique_id, 'sender': sender, 'subject': subject, 'content': content})
        except TypeError:
            logging.info(f"Node {sender_id} tried to access non-existent message")
            send_message("Mail not found", sender_id, interface)
            update_user_state(sender_id, None)

    elif step == 3:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_mail_command(sender_id, interface)
        elif len(nodes) == 1:
            recipient_id = nodes[0]['num']
            recipient_name = get_node_name(recipient_id, interface)
            send_message(f"What is the subject of your message to {recipient_name}?\nKeep it short.", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 5, 'recipient_id': recipient_id})
        else:
            send_message("There are multiple nodes with that short name. Which one would you like to leave a message for?", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 6, 'nodes': nodes})

    elif step == 4:
        if message.lower() == "d":
            unique_id = state['unique_id']
            sender_node_id = get_node_id_from_num(sender_id, interface)
            delete_mail(unique_id, sender_node_id, bbs_nodes, interface)
            send_message("The message has been deleted 🗑️", sender_id, interface)
            update_user_state(sender_id, None)
        elif message.lower() == "r":
            sender = state['sender']
            send_message(f"Send your reply to {sender} now, followed by a message with END", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 7, 'reply_to_mail_id': state['mail_id'], 'subject': f"Re: {state['subject']}", 'content': ''})
        else:
            send_message("The message has been kept in your inbox.✉️", sender_id, interface)
            update_user_state(sender_id, None)

    elif step == 5:
        subject = message
        send_message("Send your message. You can send it in multiple messages if it's too long for one.\nSend a single message with END when you're done", sender_id, interface)
        update_user_state(sender_id, {'command': 'MAIL', 'step': 7, 'recipient_id': state['recipient_id'], 'subject': subject, 'content': ''})

    elif step == 6:
        selected_node_index = int(message)
        selected_node = state['nodes'][selected_node_index]
        recipient_id = selected_node['num']
        recipient_name = get_node_name(recipient_id, interface)
        send_message(f"What is the subject of your message to {recipient_name}?\nKeep it short.", sender_id, interface)
        update_user_state(sender_id, {'command': 'MAIL', 'step': 5, 'recipient_id': recipient_id})

    elif step == 7:
        if message.lower() == "end":
            if 'reply_to_mail_id' in state:
                recipient_id = get_sender_id_by_mail_id(state['reply_to_mail_id'])  # Get the sender ID from the mail ID
            else:
                recipient_id = state.get('recipient_id')
            subject = state['subject']
            content = state['content']
            recipient_name = get_node_name(recipient_id, interface)

            sender_short_name = get_node_short_name(get_node_id_from_num(sender_id, interface), interface)
            unique_id = add_mail(get_node_id_from_num(sender_id, interface), sender_short_name, recipient_id, subject, content, bbs_nodes, interface)
            send_message(f"Mail has been posted to the mailbox of {recipient_name}.\n(╯°□°)╯📨📬", sender_id, interface)

            notification_message = f"You have a new mail message from {sender_short_name}. Check your mailbox by responding to this message with CM."
            send_message(notification_message, recipient_id, interface)

            update_user_state(sender_id, None)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 8})
        else:
            state['content'] += message + "\n"
            update_user_state(sender_id, state)

    elif step == 8:
        if message.lower() == "y":
            handle_mail_command(sender_id, interface)
        else:
            send_message("Okay, feel free to send another command.", sender_id, interface)
            update_user_state(sender_id, None)


def handle_wall_of_shame_command(sender_id, interface):
    response = "Devices with battery levels below 20%:\n"
    for node_id, node in interface.nodes.items():
        metrics = node.get('deviceMetrics', {})
        battery_level = metrics.get('batteryLevel', 101)
        if battery_level < 20:
            long_name = node['user']['longName']
            response += f"{long_name} - Battery {battery_level}%\n"
    if response == "Devices with battery levels below 20%:\n":
        response = "No devices with battery levels below 20% found."
    send_message(response, sender_id, interface)


def handle_channel_directory_command(sender_id, interface):
    response = "📚CHANNEL DIRECTORY📚\nWhat would you like to do?\n[V]iew  [P]ost\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 1})


def handle_channel_directory_steps(sender_id, message, step, state, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message
        if choice in {'b', 'back'}:
            handle_help_command(sender_id, interface, 'bbs')
            return
        if choice == 'x':
            handle_help_command(sender_id, interface)
            return
        elif choice == 'v':
            channels = get_channels()
            if channels:
                response = "Select a channel number to view:\n" + "\n".join(
                    [f"[{i}] {channel[0]}" for i, channel in enumerate(channels)])
                send_message(response, sender_id, interface)
                update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 2})
            else:
                send_message("No channels available in the directory.", sender_id, interface)
                handle_channel_directory_command(sender_id, interface)
        elif choice == 'p':
            send_message("Name your channel for the directory:", sender_id, interface)
            update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 3})

    elif step == 2:
        channel_index = int(message)
        channels = get_channels()
        if 0 <= channel_index < len(channels):
            channel_name, channel_url = channels[channel_index]
            send_message(f"Channel Name: {channel_name}\nChannel URL:\n{channel_url}", sender_id, interface)
        handle_channel_directory_command(sender_id, interface)

    elif step == 3:
        channel_name = message
        send_message("Send a message with your channel URL or PSK:", sender_id, interface)
        update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 4, 'channel_name': channel_name})

    elif step == 4:
        channel_url = message
        channel_name = state['channel_name']
        add_channel(channel_name, channel_url)
        send_message(f"Your channel '{channel_name}' has been added to the directory.", sender_id, interface)
        handle_channel_directory_command(sender_id, interface)


def format_tictactoe_board(board):
    cells = []
    for i, cell in enumerate(board):
        cells.append(str(i + 1) if cell == '-' else cell)
    rows = [" | ".join(cells[i:i + 3]) for i in range(0, 9, 3)]
    return "\n---------\n".join(rows)


def check_tictactoe_winner(board):
    winning_lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6)
    ]
    for a, b, c in winning_lines:
        if board[a] != '-' and board[a] == board[b] == board[c]:
            return board[a]
    return None


def send_tictactoe_status(recipient_id, interface, game_id, board, next_turn, status, winner):
    board_display = format_tictactoe_board(board)
    if status == 'won':
        status_line = f"Game over! {winner} wins."
    elif status == 'draw':
        status_line = "Game over! It's a draw."
    else:
        status_line = f"Next turn: {next_turn}"
    message = f"❌⭕ Tic Tac Toe ❌⭕\nGame ID: {game_id}\n{board_display}\n{status_line}"
    send_message(message, recipient_id, interface)


def create_tictactoe_game_for_players(sender_id, opponent_id, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_tictactoe_game(sender_node_id, opponent_id)
    board = "---------"
    send_tictactoe_status(sender_id, interface, game_id, board, "X", "active", None)

    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Tic Tac Toe Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Tic Tac Toe!\n"
        f"Game ID: {game_id}\n"
        f"You are O. X goes first.\n"
        f"To make a move, reply with TTT,,{game_id},,<position> or use Games > Tic Tac Toe > Make Move.\n\n"
        f"{format_tictactoe_board(board)}\n"
        "Next turn: X"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    notification_message = f"You have a new Tic Tac Toe invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)


def handle_tictactoe_command(sender_id, interface):
    response = "❌⭕ Tic Tac Toe ❌⭕\n[N]ew Game  [M]ake Move  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'TICTACTOE', 'step': 1})


def handle_tictactoe_move(sender_id, game_id, move, interface):
    game = get_tictactoe_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player_x, player_o, board, next_turn, status, winner = game
    if status != 'active':
        send_tictactoe_status(sender_id, interface, game_id, board, next_turn, status, winner)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    if sender_node_id not in [player_x, player_o]:
        send_message("You are not a player in this game.", sender_id, interface)
        return

    current_mark = 'X' if sender_node_id == player_x else 'O'
    if current_mark != next_turn:
        send_message(f"It is not your turn. Current turn: {next_turn}", sender_id, interface)
        return

    try:
        position = int(move)
    except ValueError:
        send_message("Invalid move. Send a number between 1 and 9.", sender_id, interface)
        return

    if position < 1 or position > 9:
        send_message("Invalid move. Choose a position between 1 and 9.", sender_id, interface)
        return

    index = position - 1
    if board[index] != '-':
        send_message("That position is already taken. Choose another.", sender_id, interface)
        return

    board_list = list(board)
    board_list[index] = current_mark
    updated_board = "".join(board_list)

    winner = check_tictactoe_winner(updated_board)
    if winner:
        status = 'won'
        next_turn = current_mark
    elif '-' not in updated_board:
        status = 'draw'
    else:
        next_turn = 'O' if current_mark == 'X' else 'X'

    update_tictactoe_game(game_id, updated_board, next_turn, status, winner)

    send_tictactoe_status(sender_id, interface, game_id, updated_board, next_turn, status, winner)
    opponent_id = player_o if sender_node_id == player_x else player_x
    send_tictactoe_status(opponent_id, interface, game_id, updated_board, next_turn, status, winner)


def handle_tictactoe_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TICTACTOE', 'step': 2})
        elif message == 'm':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TICTACTOE', 'step': 3})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TICTACTOE', 'step': 5})
        else:
            handle_tictactoe_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_tictactoe_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            create_tictactoe_game_for_players(sender_id, opponent_id, interface, bbs_nodes)
            update_user_state(sender_id, None)
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'TICTACTOE', 'step': 6, 'nodes': nodes})

    elif step == 3:
        game_id = message.strip()
        send_message("Enter your move (1-9):", sender_id, interface)
        update_user_state(sender_id, {'command': 'TICTACTOE', 'step': 4, 'game_id': game_id})

    elif step == 4:
        game_id = state['game_id']
        handle_tictactoe_move(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)

    elif step == 5:
        game_id = message.strip()
        game = get_tictactoe_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, _, _, board, next_turn, status, winner = game
            send_tictactoe_status(sender_id, interface, game_id, board, next_turn, status, winner)
        update_user_state(sender_id, None)

    elif step == 6:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        opponent_id = selected_node['num']
        create_tictactoe_game_for_players(sender_id, opponent_id, interface, bbs_nodes)
        update_user_state(sender_id, None)


def handle_tictactoe_move_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Tic Tac Toe command format:\nTTT,,{game_id},,{position}", sender_id, interface)
        return
    _, game_id, move = parts
    handle_tictactoe_move(sender_id, game_id, move, interface)


def format_hangman_word(secret_word, guessed_letters):
    return " ".join([letter if letter in guessed_letters else "_" for letter in secret_word])


def send_hangman_status(recipient_id, interface, game_id, secret_word, guessed_letters, attempts_left, status):
    guessed_set = set(guessed_letters.split(",")) if guessed_letters else set()
    guessed_set.discard("")
    masked = format_hangman_word(secret_word, guessed_set)
    guessed_display = ", ".join(sorted(guessed_set)) if guessed_set else "None"
    if status == 'won':
        status_line = "Game over! Word guessed."
    elif status == 'lost':
        status_line = f"Game over! Word was {secret_word}."
    else:
        status_line = "Guess a letter."
    message = (
        "🧩 Hangman 🧩\n"
        f"Game ID: {game_id}\n"
        f"Word: {masked}\n"
        f"Guessed: {guessed_display}\n"
        f"Attempts left: {attempts_left}\n"
        f"{status_line}"
    )
    send_message(message, recipient_id, interface)


def create_hangman_game_for_players(sender_id, opponent_id, secret_word, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_hangman_game(sender_node_id, opponent_id, secret_word)
    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Hangman Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Hangman!\n"
        f"Game ID: {game_id}\n"
        f"To guess a letter, reply with HANG,,{game_id},,<letter> or use Games > Hangman > Guess.\n\n"
        f"Word: {format_hangman_word(secret_word, set())}\n"
        "Attempts left: 6"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)
    notification_message = f"You have a new Hangman invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)


def handle_hangman_command(sender_id, interface):
    response = "🧩 Hangman 🧩\n[N]ew Game  [G]uess  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'HANGMAN', 'step': 1})


def handle_hangman_guess(sender_id, game_id, guess, interface):
    game = get_hangman_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player_setter, player_guesser, secret_word, guessed_letters, attempts_left, status = game
    if status != 'active':
        send_hangman_status(sender_id, interface, game_id, secret_word, guessed_letters, attempts_left, status)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    if sender_node_id != player_guesser:
        send_message("Only the guesser can make guesses in this game.", sender_id, interface)
        return

    guess = guess.lower().strip()
    if len(guess) != 1 or not guess.isalpha():
        send_message("Invalid guess. Send a single letter.", sender_id, interface)
        return

    guessed_set = set(guessed_letters.split(",")) if guessed_letters else set()
    if guess in guessed_set:
        send_message("That letter was already guessed.", sender_id, interface)
        return

    guessed_set.add(guess)
    if guess not in secret_word:
        attempts_left -= 1

    if all(letter in guessed_set for letter in secret_word):
        status = 'won'
    elif attempts_left <= 0:
        status = 'lost'

    updated_letters = ",".join(sorted(guessed_set))
    update_hangman_game(game_id, updated_letters, attempts_left, status)

    send_hangman_status(sender_id, interface, game_id, secret_word, updated_letters, attempts_left, status)
    send_hangman_status(player_setter, interface, game_id, secret_word, updated_letters, attempts_left, status)


def handle_hangman_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'HANGMAN', 'step': 2})
        elif message == 'g':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'HANGMAN', 'step': 4})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'HANGMAN', 'step': 7})
        else:
            handle_hangman_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_hangman_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            send_message("Enter the secret word for Hangman (letters only):", sender_id, interface)
            update_user_state(sender_id, {'command': 'HANGMAN', 'step': 3, 'opponent_id': opponent_id})
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'HANGMAN', 'step': 6, 'nodes': nodes})

    elif step == 3:
        secret_word = message.strip().lower()
        if not secret_word.isalpha():
            send_message("Invalid word. Use letters only.", sender_id, interface)
            return
        create_hangman_game_for_players(sender_id, state['opponent_id'], secret_word, interface, bbs_nodes)
        update_user_state(sender_id, None)

    elif step == 4:
        game_id = message.strip()
        send_message("Guess a letter:", sender_id, interface)
        update_user_state(sender_id, {'command': 'HANGMAN', 'step': 5, 'game_id': game_id})

    elif step == 5:
        game_id = state['game_id']
        handle_hangman_guess(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)

    elif step == 6:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        send_message("Enter the secret word for Hangman (letters only):", sender_id, interface)
        update_user_state(sender_id, {'command': 'HANGMAN', 'step': 3, 'opponent_id': selected_node['num']})

    elif step == 7:
        game_id = message.strip()
        game = get_hangman_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, _, _, secret_word, guessed_letters, attempts_left, status = game
            send_hangman_status(sender_id, interface, game_id, secret_word, guessed_letters, attempts_left, status)
        update_user_state(sender_id, None)


def handle_hangman_guess_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Hangman command format:\nHANG,,{game_id},,{letter}", sender_id, interface)
        return
    _, game_id, guess = parts
    handle_hangman_guess(sender_id, game_id, guess, interface)


def format_connect4_board(board):
    rows = []
    for row in range(6):
        start = row * 7
        rows.append(" ".join(board[start:start + 7]))
    header = "1 2 3 4 5 6 7"
    return f"{header}\n" + "\n".join(rows)


def check_connect4_winner(board):
    def cell(r, c):
        return board[r * 7 + c]

    for r in range(6):
        for c in range(7):
            token = cell(r, c)
            if token == '-':
                continue
            if c <= 3 and all(cell(r, c + i) == token for i in range(4)):
                return token
            if r <= 2 and all(cell(r + i, c) == token for i in range(4)):
                return token
            if r <= 2 and c <= 3 and all(cell(r + i, c + i) == token for i in range(4)):
                return token
            if r <= 2 and c >= 3 and all(cell(r + i, c - i) == token for i in range(4)):
                return token
    return None


def send_connect4_status(recipient_id, interface, game_id, board, next_turn, status, winner):
    board_display = format_connect4_board(board)
    if status == 'won':
        status_line = f"Game over! {winner} wins."
    elif status == 'draw':
        status_line = "Game over! It's a draw."
    else:
        status_line = f"Next turn: {next_turn}"
    message = f"🔴🟡 Connect Four 🔴🟡\nGame ID: {game_id}\n{board_display}\n{status_line}"
    send_message(message, recipient_id, interface)


def create_connect4_game_for_players(sender_id, opponent_id, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_connect4_game(sender_node_id, opponent_id)
    board = "-" * 42
    send_connect4_status(sender_id, interface, game_id, board, "R", "active", None)

    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Connect Four Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Connect Four!\n"
        f"Game ID: {game_id}\n"
        "You are Y. R goes first.\n"
        f"To make a move, reply with C4,,{game_id},,<column> or use Games > Connect Four > Make Move.\n\n"
        f"{format_connect4_board(board)}\n"
        "Next turn: R"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    notification_message = f"You have a new Connect Four invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)


def handle_connect4_command(sender_id, interface):
    response = "🔴🟡 Connect Four 🔴🟡\n[N]ew Game  [M]ake Move  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'CONNECT4', 'step': 1})


def handle_connect4_move(sender_id, game_id, move, interface):
    game = get_connect4_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player_r, player_y, board, next_turn, status, winner = game
    if status != 'active':
        send_connect4_status(sender_id, interface, game_id, board, next_turn, status, winner)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    if sender_node_id not in [player_r, player_y]:
        send_message("You are not a player in this game.", sender_id, interface)
        return

    current_mark = 'R' if sender_node_id == player_r else 'Y'
    if current_mark != next_turn:
        send_message(f"It is not your turn. Current turn: {next_turn}", sender_id, interface)
        return

    try:
        column = int(move)
    except ValueError:
        send_message("Invalid move. Send a column number between 1 and 7.", sender_id, interface)
        return

    if column < 1 or column > 7:
        send_message("Invalid move. Choose a column between 1 and 7.", sender_id, interface)
        return

    col_index = column - 1
    board_list = list(board)
    placed = False
    for row in range(5, -1, -1):
        index = row * 7 + col_index
        if board_list[index] == '-':
            board_list[index] = current_mark
            placed = True
            break
    if not placed:
        send_message("That column is full. Choose another.", sender_id, interface)
        return

    updated_board = "".join(board_list)
    winner = check_connect4_winner(updated_board)
    if winner:
        status = 'won'
        next_turn = current_mark
    elif '-' not in updated_board:
        status = 'draw'
    else:
        next_turn = 'Y' if current_mark == 'R' else 'R'

    update_connect4_game(game_id, updated_board, next_turn, status, winner)

    send_connect4_status(sender_id, interface, game_id, updated_board, next_turn, status, winner)
    opponent_id = player_y if sender_node_id == player_r else player_r
    send_connect4_status(opponent_id, interface, game_id, updated_board, next_turn, status, winner)


def handle_connect4_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'CONNECT4', 'step': 2})
        elif message == 'm':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'CONNECT4', 'step': 3})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'CONNECT4', 'step': 5})
        else:
            handle_connect4_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_connect4_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            create_connect4_game_for_players(sender_id, opponent_id, interface, bbs_nodes)
            update_user_state(sender_id, None)
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'CONNECT4', 'step': 6, 'nodes': nodes})

    elif step == 3:
        game_id = message.strip()
        send_message("Enter your move (column 1-7):", sender_id, interface)
        update_user_state(sender_id, {'command': 'CONNECT4', 'step': 4, 'game_id': game_id})

    elif step == 4:
        game_id = state['game_id']
        handle_connect4_move(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)

    elif step == 5:
        game_id = message.strip()
        game = get_connect4_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, _, _, board, next_turn, status, winner = game
            send_connect4_status(sender_id, interface, game_id, board, next_turn, status, winner)
        update_user_state(sender_id, None)

    elif step == 6:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        opponent_id = selected_node['num']
        create_connect4_game_for_players(sender_id, opponent_id, interface, bbs_nodes)
        update_user_state(sender_id, None)


def handle_connect4_move_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Connect Four command format:\nC4,,{game_id},,{column}", sender_id, interface)
        return
    _, game_id, move = parts
    handle_connect4_move(sender_id, game_id, move, interface)


def mastermind_feedback(secret_code, guess):
    bulls = sum(1 for s, g in zip(secret_code, guess) if s == g)
    secret_counts = {}
    guess_counts = {}
    for s, g in zip(secret_code, guess):
        if s != g:
            secret_counts[s] = secret_counts.get(s, 0) + 1
            guess_counts[g] = guess_counts.get(g, 0) + 1
    cows = sum(min(secret_counts.get(k, 0), guess_counts.get(k, 0)) for k in guess_counts)
    return bulls, cows


def send_mastermind_status(recipient_id, interface, game_id, guesses, last_feedback, status):
    if status == 'won':
        status_line = "Game over! Code cracked."
    else:
        status_line = "Make a guess (4 digits, 1-6)."
    guess_lines = guesses.split("|") if guesses else []
    history = "\n".join(guess_lines[-5:]) if guess_lines else "No guesses yet."
    feedback = last_feedback or "No feedback yet."
    message = (
        "🧠 Mastermind 🧠\n"
        f"Game ID: {game_id}\n"
        f"Recent guesses:\n{history}\n"
        f"Last feedback: {feedback}\n"
        f"{status_line}"
    )
    send_message(message, recipient_id, interface)


def create_mastermind_game_for_players(sender_id, opponent_id, secret_code, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_mastermind_game(sender_node_id, opponent_id, secret_code)
    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Mastermind Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Mastermind!\n"
        f"Game ID: {game_id}\n"
        "Guess the 4-digit code (digits 1-6).\n"
        f"To guess, reply with MM,,{game_id},,<code> or use Games > Mastermind > Guess.\n"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)
    notification_message = f"You have a new Mastermind invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)


def handle_mastermind_command(sender_id, interface):
    response = "🧠 Mastermind 🧠\n[N]ew Game  [G]uess  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 1})


def handle_mastermind_guess(sender_id, game_id, guess, interface):
    game = get_mastermind_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player_setter, player_guesser, secret_code, guesses, status, last_feedback = game
    if status != 'active':
        send_mastermind_status(sender_id, interface, game_id, guesses, last_feedback, status)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    if sender_node_id != player_guesser:
        send_message("Only the guesser can make guesses in this game.", sender_id, interface)
        return

    guess = guess.strip()
    if len(guess) != 4 or not guess.isdigit() or any(ch not in "123456" for ch in guess):
        send_message("Invalid guess. Use 4 digits, each from 1 to 6.", sender_id, interface)
        return

    bulls, cows = mastermind_feedback(secret_code, guess)
    feedback = f"{guess} -> {bulls} bulls, {cows} cows"
    updated_guesses = f"{guesses}|{feedback}" if guesses else feedback
    if bulls == 4:
        status = 'won'
    update_mastermind_game(game_id, updated_guesses, status, feedback)

    send_mastermind_status(sender_id, interface, game_id, updated_guesses, feedback, status)
    send_mastermind_status(player_setter, interface, game_id, updated_guesses, feedback, status)


def handle_mastermind_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 2})
        elif message == 'g':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 4})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 5})
        else:
            handle_mastermind_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_mastermind_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            send_message("Enter the secret 4-digit code (digits 1-6):", sender_id, interface)
            update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 3, 'opponent_id': opponent_id})
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 6, 'nodes': nodes})

    elif step == 3:
        secret_code = message.strip()
        if len(secret_code) != 4 or not secret_code.isdigit() or any(ch not in "123456" for ch in secret_code):
            send_message("Invalid code. Use 4 digits, each from 1 to 6.", sender_id, interface)
            return
        create_mastermind_game_for_players(sender_id, state['opponent_id'], secret_code, interface, bbs_nodes)
        update_user_state(sender_id, None)

    elif step == 4:
        game_id = message.strip()
        send_message("Enter your guess (4 digits, 1-6):", sender_id, interface)
        update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 7, 'game_id': game_id})

    elif step == 5:
        game_id = message.strip()
        game = get_mastermind_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, _, _, _, guesses, status, last_feedback = game
            send_mastermind_status(sender_id, interface, game_id, guesses, last_feedback, status)
        update_user_state(sender_id, None)

    elif step == 6:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        send_message("Enter the secret 4-digit code (digits 1-6):", sender_id, interface)
        update_user_state(sender_id, {'command': 'MASTERMIND', 'step': 3, 'opponent_id': selected_node['num']})

    elif step == 7:
        game_id = state['game_id']
        handle_mastermind_guess(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)


def handle_mastermind_guess_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Mastermind command format:\nMM,,{game_id},,{code}", sender_id, interface)
        return
    _, game_id, guess = parts
    handle_mastermind_guess(sender_id, game_id, guess, interface)


def parse_battleship_positions(raw_positions):
    positions = []
    for part in raw_positions.replace(" ", "").split(","):
        if not part:
            continue
        coord = part.upper()
        if len(coord) < 2:
            return None
        row = coord[0]
        col = coord[1:]
        if row not in "ABCDE" or not col.isdigit() or int(col) < 1 or int(col) > 5:
            return None
        positions.append(f"{row}{col}")
    return positions


def send_battleship_status(recipient_id, interface, game_id, p1_hits, p2_hits, next_turn, status, is_player1):
    if status == 'won':
        status_line = "Game over! All ships sunk."
    elif status == 'waiting_for_opponent':
        status_line = "Waiting for opponent to place ships."
    else:
        status_line = f"Next turn: {'You' if (next_turn == 'P1') == is_player1 else 'Opponent'}"
    hits = p1_hits if is_player1 else p2_hits
    message = (
        "🚢 Battleship Lite 🚢\n"
        f"Game ID: {game_id}\n"
        f"Your hits: {hits or 'None'}\n"
        f"{status_line}"
    )
    send_message(message, recipient_id, interface)


def create_battleship_game_for_players(sender_id, opponent_id, positions, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_battleship_game(sender_node_id, opponent_id, ",".join(positions))
    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Battleship Lite Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Battleship Lite!\n"
        f"Game ID: {game_id}\n"
        "Place 3 ship positions on a 5x5 grid (A1-E5).\n"
        f"Reply with BSSET,,{game_id},,<A1,B2,C3> or use Games > Battleship > Set Ships.\n"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)
    notification_message = f"You have a new Battleship Lite invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)


def handle_battleship_command(sender_id, interface):
    response = "🚢 Battleship Lite 🚢\n[N]ew Game  [S]et Ships  [F]ire  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 1})


def handle_battleship_set_ships(sender_id, game_id, positions, interface):
    game = get_battleship_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player1, player2, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status = game
    sender_node_id = get_node_id_from_num(sender_id, interface)
    if sender_node_id not in [player1, player2]:
        send_message("You are not a player in this game.", sender_id, interface)
        return

    if sender_node_id == player1 and p1_ships:
        send_message("You already set your ships.", sender_id, interface)
        return
    if sender_node_id == player2 and p2_ships:
        send_message("You already set your ships.", sender_id, interface)
        return

    if len(positions) != 3:
        send_message("Please provide exactly 3 ship positions.", sender_id, interface)
        return

    if sender_node_id == player1:
        p1_ships = ",".join(positions)
    else:
        p2_ships = ",".join(positions)

    if p1_ships and p2_ships:
        status = 'active'
        next_turn = 'P1'
    update_battleship_game(game_id, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status)

    send_battleship_status(sender_id, interface, game_id, p1_hits, p2_hits, next_turn, status, sender_node_id == player1)
    opponent_id = player2 if sender_node_id == player1 else player1
    send_battleship_status(opponent_id, interface, game_id, p1_hits, p2_hits, next_turn, status, opponent_id == player1)


def handle_battleship_fire(sender_id, game_id, target, interface):
    game = get_battleship_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player1, player2, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status = game
    if status != 'active':
        send_message("Game is not ready yet.", sender_id, interface)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    if sender_node_id not in [player1, player2]:
        send_message("You are not a player in this game.", sender_id, interface)
        return

    current_turn = 'P1' if sender_node_id == player1 else 'P2'
    if current_turn != next_turn:
        send_message("It is not your turn.", sender_id, interface)
        return

    target = target.strip().upper()
    positions = parse_battleship_positions(target)
    if not positions or len(positions) != 1:
        send_message("Invalid coordinate. Use A1-E5.", sender_id, interface)
        return
    target = positions[0]

    p1_hits_set = set(filter(None, p1_hits.split(","))) if p1_hits else set()
    p2_hits_set = set(filter(None, p2_hits.split(","))) if p2_hits else set()

    opponent_ships = set(filter(None, (p2_ships or "").split(","))) if sender_node_id == player1 else set(filter(None, (p1_ships or "").split(",")))
    hits_set = p1_hits_set if sender_node_id == player1 else p2_hits_set
    if target in hits_set:
        send_message("You already fired at that coordinate.", sender_id, interface)
        return

    if target in opponent_ships:
        hits_set.add(target)
        hit_message = "Hit!"
    else:
        hit_message = "Miss."

    if sender_node_id == player1:
        p1_hits = ",".join(sorted(hits_set))
    else:
        p2_hits = ",".join(sorted(hits_set))

    if opponent_ships and hits_set.issuperset(opponent_ships):
        status = 'won'
    else:
        next_turn = 'P2' if current_turn == 'P1' else 'P1'

    update_battleship_game(game_id, p1_ships, p2_ships, p1_hits, p2_hits, next_turn, status)
    send_message(hit_message, sender_id, interface)

    send_battleship_status(sender_id, interface, game_id, p1_hits, p2_hits, next_turn, status, sender_node_id == player1)
    opponent_id = player2 if sender_node_id == player1 else player1
    send_battleship_status(opponent_id, interface, game_id, p1_hits, p2_hits, next_turn, status, opponent_id == player1)


def handle_battleship_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 2})
        elif message == 's':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 4})
        elif message == 'f':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 6})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 8})
        else:
            handle_battleship_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_battleship_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            send_message("Enter 3 ship positions (A1-E5) separated by commas:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 3, 'opponent_id': opponent_id})
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 9, 'nodes': nodes})

    elif step == 3:
        positions = parse_battleship_positions(message)
        if not positions:
            send_message("Invalid positions. Use A1-E5, comma separated.", sender_id, interface)
            return
        create_battleship_game_for_players(sender_id, state['opponent_id'], positions, interface, bbs_nodes)
        update_user_state(sender_id, None)

    elif step == 4:
        game_id = message.strip()
        send_message("Enter your 3 ship positions (A1-E5) separated by commas:", sender_id, interface)
        update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 5, 'game_id': game_id})

    elif step == 5:
        positions = parse_battleship_positions(message)
        if not positions:
            send_message("Invalid positions. Use A1-E5, comma separated.", sender_id, interface)
            return
        game_id = state['game_id']
        handle_battleship_set_ships(sender_id, game_id, positions, interface)
        update_user_state(sender_id, None)

    elif step == 6:
        game_id = message.strip()
        send_message("Enter target coordinate (A1-E5):", sender_id, interface)
        update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 7, 'game_id': game_id})

    elif step == 7:
        game_id = state['game_id']
        handle_battleship_fire(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)

    elif step == 8:
        game_id = message.strip()
        game = get_battleship_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, player1, player2, _, _, p1_hits, p2_hits, next_turn, status = game
            sender_node_id = get_node_id_from_num(sender_id, interface)
            is_player1 = sender_node_id == player1
            send_battleship_status(sender_id, interface, game_id, p1_hits, p2_hits, next_turn, status, is_player1)
        update_user_state(sender_id, None)

    elif step == 9:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        send_message("Enter 3 ship positions (A1-E5) separated by commas:", sender_id, interface)
        update_user_state(sender_id, {'command': 'BATTLESHIP', 'step': 3, 'opponent_id': selected_node['num']})


def handle_battleship_set_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Battleship set command format:\nBSSET,,{game_id},,{A1,B2,C3}", sender_id, interface)
        return
    _, game_id, positions = parts
    positions_list = parse_battleship_positions(positions)
    if not positions_list:
        send_message("Invalid positions. Use A1-E5, comma separated.", sender_id, interface)
        return
    handle_battleship_set_ships(sender_id, game_id, positions_list, interface)


def handle_battleship_fire_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Battleship fire command format:\nBSFIRE,,{game_id},,{A1}", sender_id, interface)
        return
    _, game_id, target = parts
    handle_battleship_fire(sender_id, game_id, target, interface)


def send_word_chain_status(recipient_id, interface, game_id, current_word, used_words, next_turn, status, is_player1):
    chain_preview = " → ".join(used_words.split(",")[-5:])
    if status == 'won':
        status_line = "Game over!"
    else:
        status_line = f"Next turn: {'You' if (next_turn == 'P1') == is_player1 else 'Opponent'}"
    message = (
        "🔤 Word Chain 🔤\n"
        f"Game ID: {game_id}\n"
        f"Current word: {current_word}\n"
        f"Recent chain: {chain_preview}\n"
        f"{status_line}"
    )
    send_message(message, recipient_id, interface)


def create_word_chain_game_for_players(sender_id, opponent_id, start_word, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_word_chain_game(sender_node_id, opponent_id, start_word)
    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Word Chain Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Word Chain!\n"
        f"Game ID: {game_id}\n"
        f"Starting word: {start_word}\n"
        f"Reply with WC,,{game_id},,<word> or use Games > Word Chain > Play.\n"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)
    notification_message = f"You have a new Word Chain invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)


def handle_word_chain_command(sender_id, interface):
    response = "🔤 Word Chain 🔤\n[N]ew Game  [P]lay  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 1})


def handle_word_chain_play(sender_id, game_id, word, interface):
    game = get_word_chain_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player1, player2, current_word, used_words, next_turn, status = game
    if status != 'active':
        send_message("Game is not active.", sender_id, interface)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    is_player1 = sender_node_id == player1
    current_turn = 'P1' if is_player1 else 'P2'
    if current_turn != next_turn:
        send_message("It is not your turn.", sender_id, interface)
        return

    word = word.strip().lower()
    if not word.isalpha():
        send_message("Invalid word. Use letters only.", sender_id, interface)
        return

    used_list = used_words.split(",") if used_words else []
    if word in used_list:
        send_message("That word has already been used.", sender_id, interface)
        return

    if word[0] != current_word[-1]:
        send_message(f"Word must start with '{current_word[-1]}'.", sender_id, interface)
        return

    used_list.append(word)
    next_turn = 'P2' if current_turn == 'P1' else 'P1'
    update_word_chain_game(game_id, word, ",".join(used_list), next_turn, status)

    send_word_chain_status(sender_id, interface, game_id, word, ",".join(used_list), next_turn, status, is_player1)
    opponent_id = player2 if is_player1 else player1
    send_word_chain_status(opponent_id, interface, game_id, word, ",".join(used_list), next_turn, status, opponent_id == player1)


def handle_word_chain_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 2})
        elif message == 'p':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 4})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 5})
        else:
            handle_word_chain_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_word_chain_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            send_message("Enter the starting word:", sender_id, interface)
            update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 3, 'opponent_id': opponent_id})
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 6, 'nodes': nodes})

    elif step == 3:
        start_word = message.strip().lower()
        if not start_word.isalpha():
            send_message("Invalid word. Use letters only.", sender_id, interface)
            return
        create_word_chain_game_for_players(sender_id, state['opponent_id'], start_word, interface, bbs_nodes)
        update_user_state(sender_id, None)

    elif step == 4:
        game_id = message.strip()
        send_message("Enter your word:", sender_id, interface)
        update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 7, 'game_id': game_id})

    elif step == 5:
        game_id = message.strip()
        game = get_word_chain_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, player1, _, current_word, used_words, next_turn, status = game
            sender_node_id = get_node_id_from_num(sender_id, interface)
            send_word_chain_status(sender_id, interface, game_id, current_word, used_words, next_turn, status, sender_node_id == player1)
        update_user_state(sender_id, None)

    elif step == 6:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        send_message("Enter the starting word:", sender_id, interface)
        update_user_state(sender_id, {'command': 'WORD_CHAIN', 'step': 3, 'opponent_id': selected_node['num']})

    elif step == 7:
        game_id = state['game_id']
        handle_word_chain_play(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)


def handle_word_chain_play_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Word Chain command format:\nWC,,{game_id},,{word}", sender_id, interface)
        return
    _, game_id, word = parts
    handle_word_chain_play(sender_id, game_id, word, interface)


def send_trivia_status(recipient_id, interface, game_id, question, status, p1_response, p2_response, is_player1):
    if status == 'complete':
        status_line = "Results are in!"
    else:
        status_line = "Submit your answer."
    response = p1_response if is_player1 else p2_response
    message = (Mastermind / Bulls‑and‑Cows
        "🧠 Trivia 🧠\n"
        f"Game ID: {game_id}\n"
        f"Question: {question}\n"
        f"Your answer: {response or 'Not submitted'}\n"
        f"{status_line}"
    )
    send_message(message, recipient_id, interface)


def create_trivia_game_for_players(sender_id, opponent_id, question, answer, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_trivia_game(sender_node_id, opponent_id, question, answer)
    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"Trivia Game {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to Trivia!\n"
        f"Game ID: {game_id}\n"
        f"Question: {question}\n"
        f"Reply with TRIV,,{game_id},,<answer> or use Games > Trivia > Answer.\n"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)
    notification_message = f"You have a new Trivia invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)


def handle_trivia_command(sender_id, interface):
    response = "🧠 Trivia 🧠\n[N]ew Game  [A]nswer  [V]iew Game\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'TRIVIA', 'step': 1})


def handle_trivia_answer(sender_id, game_id, answer, interface):
    game = get_trivia_game(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, player1, player2, question, correct_answer, p1_response, p2_response, status = game
    sender_node_id = get_node_id_from_num(sender_id, interface)
    is_player1 = sender_node_id == player1
    if sender_node_id not in [player1, player2]:
        send_message("You are not a player in this game.", sender_id, interface)
        return

    if status != 'active':
        send_trivia_status(sender_id, interface, game_id, question, status, p1_response, p2_response, is_player1)
        return

    if is_player1 and p1_response:
        send_message("You already answered.", sender_id, interface)
        return
    if not is_player1 and p2_response:
        send_message("You already answered.", sender_id, interface)
        return

    if is_player1:
        p1_response = answer.strip()
    else:
        p2_response = answer.strip()

    if p1_response and p2_response:
        status = 'complete'

    update_trivia_game(game_id, p1_response, p2_response, status)

    send_trivia_status(sender_id, interface, game_id, question, status, p1_response, p2_response, is_player1)
    opponent_id = player2 if is_player1 else player1
    send_trivia_status(opponent_id, interface, game_id, question, status, p1_response, p2_response, opponent_id == player1)
    if status == 'complete':
        result_message = (
            f"Trivia results for game {game_id}:\n"
            f"Answer: {correct_answer}\n"
            f"P1: {p1_response}\n"
            f"P2: {p2_response}"
        )
        send_message(result_message, sender_id, interface)
        send_message(result_message, opponent_id, interface)


def handle_trivia_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Enter the short name of your opponent:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TRIVIA', 'step': 2})
        elif message == 'a':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TRIVIA', 'step': 5})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TRIVIA', 'step': 6})
        else:
            handle_trivia_command(sender_id, interface)

    elif step == 2:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_trivia_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            send_message("Enter the trivia question:", sender_id, interface)
            update_user_state(sender_id, {'command': 'TRIVIA', 'step': 3, 'opponent_id': opponent_id})
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'TRIVIA', 'step': 7, 'nodes': nodes})

    elif step == 3:
        question = message.strip()
        send_message("Enter the correct answer:", sender_id, interface)
        update_user_state(sender_id, {'command': 'TRIVIA', 'step': 4, 'opponent_id': state['opponent_id'], 'question': question})

    elif step == 4:
        answer = message.strip()
        create_trivia_game_for_players(sender_id, state['opponent_id'], state['question'], answer, interface, bbs_nodes)
        update_user_state(sender_id, None)

    elif step == 5:
        game_id = message.strip()
        send_message("Enter your answer:", sender_id, interface)
        update_user_state(sender_id, {'command': 'TRIVIA', 'step': 8, 'game_id': game_id})

    elif step == 6:
        game_id = message.strip()
        game = get_trivia_game(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, player1, _, question, _, p1_response, p2_response, status = game
            sender_node_id = get_node_id_from_num(sender_id, interface)
            send_trivia_status(sender_id, interface, game_id, question, status, p1_response, p2_response, sender_node_id == player1)
        update_user_state(sender_id, None)

    elif step == 7:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        send_message("Enter the trivia question:", sender_id, interface)
        update_user_state(sender_id, {'command': 'TRIVIA', 'step': 3, 'opponent_id': selected_node['num']})

    elif step == 8:
        game_id = state['game_id']
        handle_trivia_answer(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)


def handle_trivia_answer_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Trivia command format:\nTRIV,,{game_id},,{answer}", sender_id, interface)
        return
    _, game_id, answer = parts
    handle_trivia_answer(sender_id, game_id, answer, interface)


def send_boardgame_status(recipient_id, interface, game_id, game_type, moves, next_turn, status, is_player1):
    move_lines = moves.split("|") if moves else []
    recent = "\n".join(move_lines[-5:]) if move_lines else "No moves yet."
    if status != 'active':
        status_line = "Game over."
    else:
        status_line = f"Next turn: {'You' if (next_turn == 'P1') == is_player1 else 'Opponent'}"
    message = (
        f"♟️ {game_type.title()} Match ♟️\n"
        f"Game ID: {game_id}\n"
        f"Recent moves:\n{recent}\n"
        f"{status_line}\n"
        "Note: Moves are not validated."
    )
    send_message(message, recipient_id, interface)


def create_boardgame_match_for_players(sender_id, opponent_id, game_type, interface, bbs_nodes):
    sender_node_id = get_node_id_from_num(sender_id, interface)
    game_id = create_boardgame_match(game_type, sender_node_id, opponent_id)
    sender_short_name = get_node_short_name(sender_node_id, interface)
    opponent_name = get_node_name(opponent_id, interface)
    mail_subject = f"{game_type.title()} Match {game_id}"
    mail_content = (
        f"{sender_short_name} invited you to {game_type.title()}!\n"
        f"Game ID: {game_id}\n"
        "Moves are not validated. Use standard notation.\n"
        f"Reply with MOVE,,{game_id},,<move> or use Games > Chess/Checkers > Move.\n"
    )
    add_mail(sender_node_id, sender_short_name, opponent_id, mail_subject, mail_content, bbs_nodes, interface)
    send_message(f"Invite sent to {opponent_name}.", sender_id, interface)
    notification_message = f"You have a new {game_type.title()} invite from {sender_short_name}. Check your mailbox."
    send_message(notification_message, opponent_id, interface)


def handle_boardgame_command(sender_id, interface):
    response = "♟️ Chess/Checkers ♟️\n[N]ew Match  [M]ove  [V]iew Match\nType BACK to return."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 1})


def handle_boardgame_move(sender_id, game_id, move, interface):
    game = get_boardgame_match(game_id)
    if not game:
        send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        return

    _, game_type, player1, player2, moves, next_turn, status = game
    if status != 'active':
        send_boardgame_status(sender_id, interface, game_id, game_type, moves, next_turn, status, sender_id == player1)
        return

    sender_node_id = get_node_id_from_num(sender_id, interface)
    is_player1 = sender_node_id == player1
    current_turn = 'P1' if is_player1 else 'P2'
    if sender_node_id not in [player1, player2]:
        send_message("You are not a player in this game.", sender_id, interface)
        return
    if current_turn != next_turn:
        send_message("It is not your turn.", sender_id, interface)
        return

    move_entry = f"{'P1' if is_player1 else 'P2'}: {move.strip()}"
    updated_moves = f"{moves}|{move_entry}" if moves else move_entry
    next_turn = 'P2' if current_turn == 'P1' else 'P1'
    update_boardgame_match(game_id, updated_moves, next_turn, status)

    send_boardgame_status(sender_id, interface, game_id, game_type, updated_moves, next_turn, status, is_player1)
    opponent_id = player2 if is_player1 else player1
    send_boardgame_status(opponent_id, interface, game_id, game_type, updated_moves, next_turn, status, opponent_id == player1)


def handle_boardgame_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'n':
            send_message("Choose [C]hess or [H]checkers:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 2})
        elif message == 'm':
            send_message("Enter the game ID:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 5})
        elif message == 'v':
            send_message("Enter the game ID to view:", sender_id, interface)
            update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 6})
        else:
            handle_boardgame_command(sender_id, interface)

    elif step == 2:
        if message not in ['c', 'h']:
            send_message("Invalid choice. Use C for chess or H for checkers.", sender_id, interface)
            return
        game_type = 'chess' if message == 'c' else 'checkers'
        send_message("Enter the short name of your opponent:", sender_id, interface)
        update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 3, 'game_type': game_type})

    elif step == 3:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_boardgame_command(sender_id, interface)
        elif len(nodes) == 1:
            opponent_id = nodes[0]['num']
            create_boardgame_match_for_players(sender_id, opponent_id, state['game_type'], interface, bbs_nodes)
            update_user_state(sender_id, None)
        else:
            send_message("Multiple nodes found. Choose one:", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 4, 'nodes': nodes, 'game_type': state['game_type']})

    elif step == 4:
        try:
            selected_node_index = int(message)
        except ValueError:
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        if selected_node_index < 0 or selected_node_index >= len(state['nodes']):
            send_message("Invalid selection. Try again.", sender_id, interface)
            return
        selected_node = state['nodes'][selected_node_index]
        create_boardgame_match_for_players(sender_id, selected_node['num'], state['game_type'], interface, bbs_nodes)
        update_user_state(sender_id, None)

    elif step == 5:
        game_id = message.strip()
        send_message("Enter your move:", sender_id, interface)
        update_user_state(sender_id, {'command': 'BOARDGAME', 'step': 7, 'game_id': game_id})

    elif step == 6:
        game_id = message.strip()
        game = get_boardgame_match(game_id)
        if not game:
            send_message("Game not found. Check the Game ID and try again.", sender_id, interface)
        else:
            _, game_type, player1, _, moves, next_turn, status = game
            sender_node_id = get_node_id_from_num(sender_id, interface)
            send_boardgame_status(sender_id, interface, game_id, game_type, moves, next_turn, status, sender_node_id == player1)
        update_user_state(sender_id, None)

    elif step == 7:
        game_id = state['game_id']
        handle_boardgame_move(sender_id, game_id, message, interface)
        update_user_state(sender_id, None)


def handle_boardgame_move_command(sender_id, message, interface):
    parts = message.split(",,", 2)
    if len(parts) != 3:
        send_message("Move command format:\nMOVE,,{game_id},,{move}", sender_id, interface)
        return
    _, game_id, move = parts
    handle_boardgame_move(sender_id, game_id, move, interface)


def handle_send_mail_command(sender_id, message, interface, bbs_nodes):
    try:
        parts = message.split(",,", 3)
        if len(parts) != 4:
            send_message("Send Mail Quick Command format:\nSM,,{short_name},,{subject},,{message}", sender_id, interface)
            return

        _, short_name, subject, content = parts
        nodes = get_node_info(interface, short_name.lower())
        if not nodes:
            send_message(f"Node with short name '{short_name}' not found.", sender_id, interface)
            return
        if len(nodes) > 1:
            send_message(f"Multiple nodes with short name '{short_name}' found. Please be more specific.", sender_id,
                         interface)
            return

        recipient_id = nodes[0]['num']
        recipient_name = get_node_name(recipient_id, interface)
        sender_short_name = get_node_short_name(get_node_id_from_num(sender_id, interface), interface)

        unique_id = add_mail(get_node_id_from_num(sender_id, interface), sender_short_name, recipient_id, subject,
                             content, bbs_nodes, interface)
        send_message(f"Mail has been sent to {recipient_name}.", sender_id, interface)

        notification_message = f"You have a new mail message from {sender_short_name}. Check your mailbox by responding to this message with CM."
        send_message(notification_message, recipient_id, interface)

    except Exception as e:
        logging.error(f"Error processing send mail command: {e}")
        send_message("Error processing send mail command.", sender_id, interface)


def handle_check_mail_command(sender_id, interface):
    try:
        sender_node_id = get_node_id_from_num(sender_id, interface)
        mail = get_mail(sender_node_id)
        if not mail:
            send_message("You have no new messages.", sender_id, interface)
            return

        response = "📬 You have the following messages:\n"
        for i, msg in enumerate(mail):
            response += f"{i + 1:02d}. From: {msg[1]}, Subject: {msg[2]}\n"
        response += "\nPlease reply with the number of the message you want to read."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'CHECK_MAIL', 'step': 1, 'mail': mail})

    except Exception as e:
        logging.error(f"Error processing check mail command: {e}")
        send_message("Error processing check mail command.", sender_id, interface)


def handle_read_mail_command(sender_id, message, state, interface):
    try:
        mail = state.get('mail', [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(mail):
            send_message("Invalid message number. Please try again.", sender_id, interface)
            return

        mail_id = mail[message_number][0]
        sender_node_id = get_node_id_from_num(sender_id, interface)
        sender, date, subject, content, unique_id = get_mail_content(mail_id, sender_node_id)
        response = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{content}"
        send_message(response, sender_id, interface)
        send_message("What would you like to do with this message?\n[K]eep  [D]elete  [R]eply", sender_id, interface)
        update_user_state(sender_id, {'command': 'CHECK_MAIL', 'step': 2, 'mail_id': mail_id, 'unique_id': unique_id, 'sender': sender, 'subject': subject, 'content': content})

    except ValueError:
        send_message("Invalid input. Please enter a valid message number.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error processing read mail command: {e}")
        send_message("Error processing read mail command.", sender_id, interface)


def handle_delete_mail_confirmation(sender_id, message, state, interface, bbs_nodes):
    try:
        choice = message.lower().strip()
        if len(choice) == 2 and choice[1] == 'x':
            choice = choice[0]

        if choice == 'd':
            unique_id = state['unique_id']
            sender_node_id = get_node_id_from_num(sender_id, interface)
            delete_mail(unique_id, sender_node_id, bbs_nodes, interface)
            send_message("The message has been deleted 🗑️", sender_id, interface)
            update_user_state(sender_id, None)
        elif choice == 'r':
            sender = state['sender']
            send_message(f"Send your reply to {sender} now, followed by a message with END", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 7, 'reply_to_mail_id': state['mail_id'], 'subject': f"Re: {state['subject']}", 'content': ''})
        else:
            send_message("The message has been kept in your inbox.✉️", sender_id, interface)
            update_user_state(sender_id, None)

    except Exception as e:
        logging.error(f"Error processing delete mail confirmation: {e}")
        send_message("Error processing delete mail confirmation.", sender_id, interface)



def handle_post_bulletin_command(sender_id, message, interface, bbs_nodes):
    try:
        parts = message.split(",,", 3)
        if len(parts) != 4:
            send_message("Post Bulletin Quick Command format:\nPB,,{board_name},,{subject},,{content}", sender_id, interface)
            return

        _, board_name, subject, content = parts
        sender_short_name = get_node_short_name(get_node_id_from_num(sender_id, interface), interface)

        unique_id = add_bulletin(board_name, sender_short_name, subject, content, bbs_nodes, interface)
        send_message(f"Your bulletin '{subject}' has been posted to {board_name}.", sender_id, interface)

        if board_name.lower() == "urgent":
            notification_message = f"💥NEW URGENT BULLETIN💥\nFrom: {sender_short_name}\nTitle: {subject}"
            send_message(notification_message, BROADCAST_NUM, interface)

    except Exception as e:
        logging.error(f"Error processing post bulletin command: {e}")
        send_message("Error processing post bulletin command.", sender_id, interface)


def handle_check_bulletin_command(sender_id, message, interface):
    try:
        # Split the message only once
        parts = message.split(",,", 1)
        if len(parts) != 2 or not parts[1].strip():
            send_message("Check Bulletins Quick Command format:\nCB,,{board_name}", sender_id, interface)
            return

        board_name = parts[1].strip()
        bulletins = get_bulletins(board_name)
        if not bulletins:
            send_message(f"No bulletins available on {board_name} board.", sender_id, interface)
            return

        response = f"📰 Bulletins on {board_name} board:\n"
        for i, bulletin in enumerate(bulletins):
            response += f"[{i+1:02d}] Subject: {bulletin[1]}, From: {bulletin[2]}, Date: {bulletin[3]}\n"
        response += "\nPlease reply with the number of the bulletin you want to read."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'CHECK_BULLETIN', 'step': 1, 'board_name': board_name, 'bulletins': bulletins})

    except Exception as e:
        logging.error(f"Error processing check bulletin command: {e}")
        send_message("Error processing check bulletin command.", sender_id, interface)

def handle_read_bulletin_command(sender_id, message, state, interface):
    try:
        bulletins = state.get('bulletins', [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(bulletins):
            send_message("Invalid bulletin number. Please try again.", sender_id, interface)
            return

        bulletin_id = bulletins[message_number][0]
        sender, date, subject, content, unique_id = get_bulletin_content(bulletin_id)
        response = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{content}"
        send_message(response, sender_id, interface)

        update_user_state(sender_id, None)

    except ValueError:
        send_message("Invalid input. Please enter a valid bulletin number.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error processing read bulletin command: {e}")
        send_message("Error processing read bulletin command.", sender_id, interface)


def handle_post_channel_command(sender_id, message, interface):
    try:
        parts = message.split("|", 3)
        if len(parts) != 3:
            send_message("Post Channel Quick Command format:\nCHP,,{channel_name},,{channel_url}", sender_id, interface)
            return

        _, channel_name, channel_url = parts
        bbs_nodes = interface.bbs_nodes
        add_channel(channel_name, channel_url, bbs_nodes, interface)
        send_message(f"Channel '{channel_name}' has been added to the directory.", sender_id, interface)

    except Exception as e:
        logging.error(f"Error processing post channel command: {e}")
        send_message("Error processing post channel command.", sender_id, interface)


def handle_check_channel_command(sender_id, interface):
    try:
        channels = get_channels()
        if not channels:
            send_message("No channels available in the directory.", sender_id, interface)
            return

        response = "Available Channels:\n"
        for i, channel in enumerate(channels):
            response += f"{i + 1:02d}. Name: {channel[0]}\n"
        response += "\nPlease reply with the number of the channel you want to view."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'CHECK_CHANNEL', 'step': 1, 'channels': channels})

    except Exception as e:
        logging.error(f"Error processing check channel command: {e}")
        send_message("Error processing check channel command.", sender_id, interface)


def handle_read_channel_command(sender_id, message, state, interface):
    try:
        channels = state.get('channels', [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(channels):
            send_message("Invalid channel number. Please try again.", sender_id, interface)
            return

        channel_name, channel_url = channels[message_number]
        response = f"Channel Name: {channel_name}\nChannel URL: {channel_url}"
        send_message(response, sender_id, interface)

        update_user_state(sender_id, None)

    except ValueError:
        send_message("Invalid input. Please enter a valid channel number.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error processing read channel command: {e}")
        send_message("Error processing read channel command.", sender_id, interface)


def handle_list_channels_command(sender_id, interface):
    try:
        channels = get_channels()
        if not channels:
            send_message("No channels available in the directory.", sender_id, interface)
            return

        response = "Available Channels:\n"
        for i, channel in enumerate(channels):
            response += f"{i+1:02d}. Name: {channel[0]}\n"
        response += "\nPlease reply with the number of the channel you want to view."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'LIST_CHANNELS', 'step': 1, 'channels': channels})

    except Exception as e:
        logging.error(f"Error processing list channels command: {e}")
        send_message("Error processing list channels command.", sender_id, interface)


def handle_quick_help_command(sender_id, interface):
    response = (
        "✈️QUICK COMMANDS✈️\nSend command below for usage info:\n"
        "SM,, - Send Mail\nCM - Check Mail\nPB,, - Post Bulletin\nCB,, - Check Bulletins\n"
        "TTT,, - Tic Tac Toe Move\nHANG,, - Hangman Guess\nC4,, - Connect Four Move\n"
        "MM,, - Mastermind Guess\nBSSET,, - Battleship Set Ships\nBSFIRE,, - Battleship Fire\n"
        "WC,, - Word Chain Play\nTRIV,, - Trivia Answer\nMOVE,, - Chess/Checkers Move\n"
    )
    send_message(response, sender_id, interface)
    
def handle_time_command(sender_id, interface, menu_name=None):
    now = datetime.datetime.now()
    send_message(now.strftime("%Y-%m-%d %H:%M:%S"), sender_id, interface)


def handle_sunmoon_command(sender_id, interface, menu_name=None):
    latitude = 32.2226
    longitude = -110.9747

    try:
        sun = Sun(latitude, longitude)
        sunrise_utc = sun.get_sunrise_time()
        sunset_utc = sun.get_sunset_time()
        response = (
            "🌅🌙 SunMoon (UTC)\n"
            f"Sunrise: {sunrise_utc.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Sunset:  {sunset_utc.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_message(response, sender_id, interface)
    except SunTimeException as e:
        send_message(f"Sun/Moon time error: {e}", sender_id, interface)
    except Exception as e:
        send_message(f"Error getting sunrise/sunset: {e}", sender_id, interface)


def _load_dictionary():
    global _dictionary_cache
    if _dictionary_cache is None:
        with open(DICTIONARY_PATH, 'r', encoding='utf-8') as file:
            _dictionary_cache = json.load(file)
    return _dictionary_cache


def handle_dictionary_command(sender_id, interface):
    response = "📚 DICTIONARY 📚\nPress [P] to send a word or E[X]IT."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'DICTIONARY', 'step': 1})


def handle_dictionary_steps(sender_id, message, step, state, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'x':
            handle_help_command(sender_id, interface, 'utilities')
            return
        if message == 'p':
            send_message("Send the word you want to define:", sender_id, interface)
            update_user_state(sender_id, {'command': 'DICTIONARY', 'step': 2})
        else:
            send_message("Invalid choice. Press [P] to send a word or E[X]IT.", sender_id, interface)
    elif step == 2:
        word = message.strip()
        if not word:
            send_message("Please send a word to define.", sender_id, interface)
            return
        try:
            dictionary = _load_dictionary()
            definition = dictionary.get(word)
            if not definition:
                send_message(f"No definition found for '{word}'.", sender_id, interface)
            else:
                response = f"{word.capitalize()}: {definition}"
                send_message(response, sender_id, interface)
        except FileNotFoundError:
            send_message("Dictionary data not found. Please contact the administrator.", sender_id, interface)
        except json.JSONDecodeError:
            send_message("Dictionary data is invalid. Please contact the administrator.", sender_id, interface)
        except Exception as e:
            send_message(f"Error looking up definition: {e}", sender_id, interface)
        handle_dictionary_command(sender_id, interface)


def handle_adsb_command(sender_id, interface):
    response = "✈️ ADS-B ✈️\nChoose [L]ast plane, [T]op 10, or E[X]IT."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'ADSB', 'step': 1})


def _run_adsb_parser(mode):
    try:
        result = subprocess.run(
            ["python3", ADSB_PARSER_PATH, "--mode", mode],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        return output if output else "No output returned from ADS-B parser."
    except FileNotFoundError:
        return "ADSB parser script not found. Please contact the administrator."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or "Unknown error running ADS-B parser."
        return f"Error running ADS-B parser: {error_output}"


def handle_adsb_steps(sender_id, message, step, state, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'x':
            handle_help_command(sender_id, interface, 'utilities')
            return
        if message == 'l':
            response = _run_adsb_parser("latest")
            send_message(response, sender_id, interface)
            handle_adsb_command(sender_id, interface)
        elif message == 't':
            response = _run_adsb_parser("last10")
            send_message(response, sender_id, interface)
            handle_adsb_command(sender_id, interface)
        else:
            send_message("Invalid choice. Choose [L]ast plane, [T]op 10, or E[X]IT.", sender_id, interface)


def handle_ollama_command(sender_id, interface):
    response = "🤖 Ollama 🤖\nPress [P] to send a prompt or E[X]IT."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'OLLAMA', 'step': 1})


def handle_ollama_steps(sender_id, message, step, state, interface):
    message = message.strip()
    if len(message) == 2 and message[1].lower() == 'x':
        message = message[0]

    if step == 1:
        choice = message.lower()
        if choice == 'x':
            handle_help_command(sender_id, interface, 'utilities')
            return
        if choice == 'p':
            send_message("Send the prompt you want to ask Ollama:", sender_id, interface)
            update_user_state(sender_id, {'command': 'OLLAMA', 'step': 2})
        else:
            send_message("Invalid choice. Press [P] to send a prompt or E[X]IT.", sender_id, interface)
    elif step == 2:
        prompt = message.strip()
        if not prompt:
            send_message("Please send a prompt for Ollama.", sender_id, interface)
            return
        try:
            response = ask_ollama(prompt)
            send_message(response, sender_id, interface)
        except Exception as e:
            send_message(f"Error getting Ollama response: {e}", sender_id, interface)
        handle_ollama_command(sender_id, interface)


def handle_wx_command(sender_id, interface):
    response = "🌦️ Weather (WX) 🌦️\nSend a number from 1-5 for history, or E[X]IT."
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'WX', 'step': 1})


def _run_wx_parser(entries):
    try:
        result = subprocess.run(
            ["python3", WX_PARSER_PATH, str(entries)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        return output if output else "No output returned from WX parser."
    except FileNotFoundError:
        return "WX parser script not found. Please contact the administrator."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or "Unknown error running WX parser."
        return f"Error running WX parser: {error_output}"


def handle_wx_steps(sender_id, message, step, state, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        if message == 'x':
            handle_help_command(sender_id, interface, 'utilities')
            return
        try:
            entries = int(message)
        except ValueError:
            send_message("Invalid choice. Send a number from 1-5 or E[X]IT.", sender_id, interface)
            return

        if entries < 1 or entries > 5:
            send_message("Please choose a number from 1-5.", sender_id, interface)
            return

        response = _run_wx_parser(entries)
        send_message(response, sender_id, interface)
        handle_wx_command(sender_id, interface)
