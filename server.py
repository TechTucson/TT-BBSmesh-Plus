#!/usr/bin/env python3

"""
TC²-BBS Server for Meshtastic by TheCommsChannel (TC²)
Date: 07/14/2024
Version: 0.1.6

Description:
The system allows for mail message handling, bulletin boards, and a channel
directory. It uses a configuration file for setup details and an SQLite3
database for data storage. Mail messages and bulletins are synced with
other BBS servers listed in the config.ini file.
"""

import logging
import os
import time

from config_init import initialize_config, get_interface, init_cli_parser, merge_config
from db_operations import (
    DB_FILE,
    backup_database,
    clear_database,
    get_database_size_bytes,
    initialize_database,
)
from js8call_integration import JS8CallClient
from message_processing import on_receive
from meshtastic import BROADCAST_NUM
from pubsub import pub
from utils import send_message

# General logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# JS8Call logging
js8call_logger = logging.getLogger('js8call')
js8call_logger.setLevel(logging.DEBUG)
js8call_handler = logging.StreamHandler()
js8call_handler.setLevel(logging.DEBUG)
js8call_formatter = logging.Formatter('%(asctime)s - JS8Call - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
js8call_handler.setFormatter(js8call_formatter)
js8call_logger.addHandler(js8call_handler)

def display_banner():
 banner = """
████████╗███████╗ ██████╗██╗  ██╗    ████████╗██╗   ██╗ ██████╗███████╗ ██████╗ ███╗   ██╗
╚══██╔══╝██╔════╝██╔════╝██║  ██║    ╚══██╔══╝██║   ██║██╔════╝██╔════╝██╔═══██╗████╗  ██║
   ██║   █████╗  ██║     ███████║       ██║   ██║   ██║██║     ███████╗██║   ██║██╔██╗ ██║
   ██║   ██╔══╝  ██║     ██╔══██║       ██║   ██║   ██║██║     ╚════██║██║   ██║██║╚██╗██║
   ██║   ███████╗╚██████╗██║  ██║       ██║   ╚██████╔╝╚██████╗███████║╚██████╔╝██║ ╚████║
   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝       ╚═╝    ╚═════╝  ╚═════╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝

TechTucson
	"""
 print(banner)

def main():
    display_banner()
    args = init_cli_parser()
    config_file = None
    if args.config is not None:
        config_file = args.config
    system_config = initialize_config(config_file)

    merge_config(system_config, args)

    interface = get_interface(system_config)
    interface.bbs_nodes = system_config['bbs_nodes']
    interface.allowed_nodes = system_config['allowed_nodes']

    logging.info(f"TC²-BBS is running on {system_config['interface_type']} interface...")

    backup_done = False
    if args.dbbackup:
        backup_path = None if args.dbbackup is True else args.dbbackup
        backup_database(backup_path)
        backup_done = True

    if args.cleandb:
        if os.path.exists(DB_FILE):
            try:
                response = input("Backup database before cleanup? [y/N]: ").strip().lower()
            except EOFError:
                response = ""
            if response in {"y", "yes"} and not backup_done:
                backup_path = None if args.dbbackup is True else args.dbbackup
                backup_database(backup_path)
        logging.info("Clearing database file before startup.")
        clear_database()

    initialize_database()
    db_size_bytes = get_database_size_bytes()
    db_size_mb = db_size_bytes / (1024 * 1024)
    logging.info(f"Database size: {db_size_mb:.2f} MB")
    if db_size_bytes >= 10 * 1024 * 1024:
        send_message(
            f"Database size is {db_size_mb:.2f} MB and has reached the 10 MB threshold.",
            BROADCAST_NUM,
            interface
        )

    def receive_packet(packet, interface):
        on_receive(packet, interface)

    pub.subscribe(receive_packet, system_config['mqtt_topic'])

    # Initialize and start JS8Call Client if configured
    js8call_client = JS8CallClient(interface)
    js8call_client.logger = js8call_logger

    if js8call_client.db_conn:
        js8call_client.connect()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Shutting down the server...")
        interface.close()
        if js8call_client.connected:
            js8call_client.close()

if __name__ == "__main__":
    main()
