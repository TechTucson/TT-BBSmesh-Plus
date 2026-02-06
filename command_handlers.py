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
    add_channel, get_channels, get_sender_id_by_mail_id
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
            menu_str += "[B]BS\n"
        elif item.strip() == 'U':
            menu_str += "[U]tilities\n"
        elif item.strip() == 'X':
            menu_str += "E[X]IT\n"
        elif item.strip() == 'M':
            menu_str += "[M]ail\n"
        elif item.strip() == 'C':
            menu_str += "[C]hannel Dir\n"
        elif item.strip() == 'J':
            menu_str += "[J]S8CALL\n"
        elif item.strip() == 'S':
            menu_str += "[S]tats [1]\n"
        elif item.strip() == 'F':
            menu_str += "[F]ortune [2]\n"
        elif item.strip() == 'W':
            menu_str += "[W]all of Shame [3]\n"
        elif item.strip() == 'T':
            menu_str += "[T]ime [4]\n"
        elif item.strip() == 'N':
            menu_str += "Su[N]Moon [5]\n"
        elif item.strip() == 'D':
            menu_str += "[D]efine [6]\n"
        elif item.strip() == 'A':
            menu_str += "[A]DSB [7]\n"
        elif item.strip() == 'O':
            menu_str += "[O]llama [8]\n"
        elif item.strip() == 'H':
            menu_str += "Weat[H]er (WX) [9]\n"
    return menu_str


def handle_help_command(sender_id, interface, menu_name=None):
    if menu_name:
        update_user_state(sender_id, {'command': 'MENU', 'menu': menu_name, 'step': 1})
        if menu_name == 'bbs':
            response = build_menu(bbs_menu_items, "📰BBS Menu📰")
        elif menu_name == 'utilities':
            response = build_menu(utilities_menu_items, "🛠️Utilities Menu🛠️")
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
    response = "✉️Mail Menu✉️\nWhat would you like to do with mail?\n[R]ead  [S]end E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'MAIL', 'step': 1})



def handle_bulletin_command(sender_id, interface):
    response = "📰Bulletin Menu📰\nWhich board would you like to enter?\n[G]eneral  [I]nfo  [N]ews  [U]rgent"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'BULLETIN_MENU', 'step': 1})


def handle_exit_command(sender_id, interface):
    send_message("Type 'HELP' for a list of commands.", sender_id, interface)
    update_user_state(sender_id, None)


def handle_stats_command(sender_id, interface):
    response = "📊Stats Menu📊\nWhat stats would you like to view?\n[N]odes  [H]ardware  [R]oles  E[X]IT"
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
    response = "📚CHANNEL DIRECTORY📚\nWhat would you like to do?\n[V]iew  [P]ost  E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 1})


def handle_channel_directory_steps(sender_id, message, step, state, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message
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
    response = ("✈️QUICK COMMANDS✈️\nSend command below for usage info:\nSM,, - Send "
                "Mail\nCM - Check Mail\nPB,, - Post Bulletin\nCB,, - Check Bulletins\n")
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
