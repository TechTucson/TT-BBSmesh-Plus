# (TechTucson) TC²-BBS Meshtastic Version

- This is the TC²-BBS system integrated with Meshtastic devices. The system allows for message handling, bulletin boards, mail systems, and a channel directory.
- TC2 over at https://github.com/TheCommsChannel has done some great work with the TC²-BBS system, this project blends various topics that have interested me for a while, meshtastic, python, and in essence emergency communications. By interested I mean I consider myself a novice, I figured I would take the opportunity to learn more about these topics by adding functionality to this already great resource.
- I am adding on top of something that is already built 1:) because why reinvent the wheel 2:) I am learning
- Inspiration came initially not from TC2 but from this repo: https://github.com/SpudGunMan/meshing-around

## Proposed enhancements

- TC²-BBS already comes with the essentials which include a BBS, Mail, and even JS8 Integration. The Integrations that I am thinking about at the moment are:
  - Adding a Bot that tells you the time.
  - Adding a Bot that tells you the sunset/sunrise.
  - Adding a Dictionary
    - This one is a bit tricky ( at least for me) Definitions are more than the length allowed in a single message. Proof of concept will be to display the first X characters of the definition with follow-up work to send the entire definition in chunks.   
  - Adding some sort of ADSB Functionality
  - Adding some sort of APRS Functionality
- Subsequent README files as well as examples will be added for each of these enhancements 



## Setup
- Believe it or not, I am attempting to do this solely on a Windows Machine and port this at a future time to my SBCs Running Linux. Why Windows? Well it's running on a lot more things, Figured I'd try to make it easier on the entry-level folks giving things a try.
### Requirements

- Python 3.x
  - https://www.python.org/downloads/
- Meshtastic
  - I am Using Lora, but you are free to use any device you have or you'd like ( as long as they can run Meshtastic)
- pypubsub
- ADSB
  - https://github.com/gvanem/Dump1090
  - RTL-SDR V3
  - https://github.com/nfacha/adsb-stats-logger/


### Installation

1. Clone the repository:
```sh
[git clone https://github.com/TechTucson/TT-BBSmesh-Plus.git]
cd TT-BBSmesh-Plus
   ```

2. Set up a Python virtual environment:  

    ```sh
   python -m venv venv  
   ```
3. Activate the virtual environment:  
    ```sh
   venv\Scripts\activate  
   ```
4. Install the required packages:  
   
   ```sh
   pip install -r requirements.txt
   ```

5. Rename `example_config.ini`:

   ```sh
   cp example_config.ini config.ini
   ```

6. Set up the configuration in `config.ini`:  

   You'll need to open up the config.ini file in a text editor and make your changes following the instructions below
   
   **[interface]**  
   If using `type = serial` and you have multiple devices connected, you will need to uncomment the `port =` line and enter the port of your device. While the client can use Bluetooth and TCP, we'll focus on a directly connected device. (Through USB)   
   
   Windows Example:  
   `port = COM3`   
   
 
   **[sync]**  
   Enter a list of other BBS nodes you would like to sync messages and bulletins with. Separate each by comma and no spaces as shown in the example below.   
   You can find the nodeID in the menu under `Radio Configuration > User` for each node, or use this script for getting nodedb data from a device:  
   
   [Meshtastic-Python-Examples/print-nodedb.py at main · pdxlocations/Meshtastic-Python-Examples (github.com)](https://github.com/pdxlocations/Meshtastic-Python-Examples/blob/main/print-nodedb.py)  
   
   Example Config:  
   
   ```ini
   [interface]  
   type = serial  
   port = COM6  
    
   
   [sync]  
   bbs_nodes = !f53f4abc,!f3abc123  
   ```

### Running the Server

Run the server with:

```sh
python server.py
```

Be sure you've followed the Python virtual environment steps above and activated it before running.

## Command line arguments
```
$ python server.py --help

████████╗ ██████╗██████╗       ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔════╝╚════██╗      ██╔══██╗██╔══██╗██╔════╝
   ██║   ██║      █████╔╝█████╗██████╔╝██████╔╝███████╗
   ██║   ██║     ██╔═══╝ ╚════╝██╔══██╗██╔══██╗╚════██║
   ██║   ╚██████╗███████╗      ██████╔╝██████╔╝███████║
   ╚═╝    ╚═════╝╚══════╝      ╚═════╝ ╚═════╝ ╚══════╝
Meshtastic Version

usage: server.py [-h] [--config CONFIG] [--interface-type {serial,tcp}] [--port PORT] [--host HOST] [--mqtt-topic MQTT_TOPIC]

Meshtastic BBS system

options:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        System configuration file
  --interface-type {serial,tcp}, -i {serial,tcp}
                        Node interface type
  --port PORT, -p PORT  Serial port
  --host HOST           TCP host address
  --mqtt-topic MQTT_TOPIC, -t MQTT_TOPIC
                        MQTT topic to subscribe
```

# Extending Functionality
## Time
Let's  start by adding the time Functionality. We'll need to update three files:
- **config.ini**
- **message_processing.py**
- **command_handlers.py**
I have placed examples of the code in the examples folder.
## Sunrise and Sunset 
Example in folder


## Automatically run at boot

- While this is possible we won't focus on this, please refer to (https://github.com/TechTucson/TC2-BBS-mesh/blob/main/README.md)

## Radio Configuration

Note: There have been reports of issues with some device roles that may allow the BBS to communicate for a short time, but then the BBS will stop responding to requests. 

The following device roles have been working: 
- **Client**
- **Router_Client**

## Features

- **Mail System**: Send and receive mail messages.
- **Bulletin Boards**: Post and view bulletins on various boards.
- **Channel Directory**: Add and view channels in the directory.
- **Statistics**: View statistics about nodes, hardware, and roles.
- **Wall of Shame**: View devices with low battery levels.
- **Fortune Teller**: Get a random fortune. Pulls from the fortunes.txt file. Feel free to edit this file remove or add more if you like.

## Usage

You interact with the BBS by sending direct messages to the node that's connected to the system running the Python script. Sending any message to it will get a response with the main menu.  
Make selections by sending messages based on the letter or number in brackets - Send M for [M]ail Menu for example.

A video of it in use is available on our YouTube channel:

[![TC²-BBS-Mesh](https://img.youtube.com/vi/d6LhY4HoimU/0.jpg)](https://www.youtube.com/watch?v=d6LhY4HoimU)


## License

GNU General Public License v3.0

