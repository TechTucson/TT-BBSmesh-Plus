# (TechTucson) TT-BBSMesh Plus Meshtastic Version

This project extends the TC²-BBS system integrated with Meshtastic devices. It provides core BBS functionality including message handling, bulletin boards, mail services, and a channel directory.

TC2 (https://github.com/TheCommsChannel) has done excellent work building TC²-BBS. This project builds directly on that foundation, bringing together several areas I’ve been interested in for a while: Meshtastic, Python, and emergency communications.

I still consider myself a novice in these spaces, so this effort is as much about learning as it is about adding functionality. Rather than reinventing the wheel, I chose to build on an existing, well-designed project, both for efficiency and as a hands-on way to deepen my understanding.

While TC²-BBS forms the core of this work, the original inspiration actually came from this repository: https://github.com/SpudGunMan/meshing-around

## 
Added a How To Readme : https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/HOWTO.md
## Added Enhancements

- TC²-BBS already comes with the essentials which include a BBS, Mail, and even JS8 Integration. The Integrations that I have completed at the moment are:
  - Adding a Bot that tells you the time.
    - Take a Look here: https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/documentation/TIME.md   

  - Adding a Bot that tells you the sunset/sunrise.
    - Take a Look here: https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/documentation/SUN.md   
   
  - Adding a Dictionary
    - Take a Look here: https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/documentation/ENHANCEMENT-DICTIONARY.md   
  - Adding some sort of ADSB Functionality
    - You can see the latest ( and the last 10) planes your ADSB Receiver has logged.
    - Take a look here: https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/documentation/ENHANCEMENT-ADSB.md
  - Added a Local LLM using Ollama
    - Take a Look here: Coming Soon
  - Added a Weather Tool This takes audio from National Weather Forecast and SAFE Creates Text, Exposes that text and is presented to the user. 
    - Take a Look here: https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/documentation/ENHANCEMENT-WX.md 
  - Added a Readiness menu with check-ins, team roster, go-bag checklist, and radio/comms reference.

   
## Added Games
- Tic Tac Toe
- Hangman
- Connect Four
- MasterMind
- Battleship
- WordChain
- Trivia
- Chess/Checkers

## Added Readiness Menu
- Check-In
- Team Roster
- Go Bag Checklist
- Radio/Comms Reference

## Upcoming Enhancements
  - Adding some sort of APRS Functionality

## Setup
- Believe it or not, I am attempting to do this solely on a Windows Machine and port this at a future time to my SBCs Running Linux. Why Windows? Well it's running on a lot more things, Figured I'd try to make it easier on the entry-level folks giving things a try.
  - Since we are testing and adding functionality, I have moved this to a MiniPC Running Ubuntu 24.04. 
### Requirements

- Python 3.x
  - https://www.python.org/downloads/
- Meshtastic
  - I am Using Lora, but you are free to use any device you have or you'd like ( as long as they can run Meshtastic)
- ADSB
  - RTL-SDR V3
    - ```sudo docker run -d   --name readsb3   --device=/dev/bus/usb   -p 8090:8080   -p 30003:30003   -p 30005:30005   --restart unless-stopped   ghcr.io/wiedehopf/readsb:latest   --device-type rtlsdr  --write-json yes   --json-location /run/readsb   --write-json-every 1```
  - ADSB Parser Dockerfile
    - The Tools/docker/adsb Dockerfile must be built and running for the ADSBParser utility to function.
    - Ensure the host machine can access the RTL-SDR (rtl_sdr works and the device is visible to Docker).
- Weatherstac (WXparse)
  - The Tools/docker/weatherstac stack includes:
    - `sdr`: tunes NOAA weather radio frequencies with `rtl_fm`, captures audio with `sox`, decodes SAME alerts with `multimon-ng`, and uses Whisper to transcribe voice audio into a shared SQLite database.
    - `api`: serves the latest/history records from the shared database and provides a simple WebSocket-backed dashboard on port 9000.
  - The host must have a working RTL-SDR setup (`rtl_sdr` runs and the USB device is visible to Docker).
  - ```sudo docker -d compose up``` 

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
   source venv/bin/activate   ```
5. Install the required packages:  
   
   ```sh
   pip install -r requirements.txt
   ```

7. Set up the configuration in `config.ini`:  

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
████████╗███████╗ ██████╗██╗  ██╗    ████████╗██╗   ██╗ ██████╗███████╗ ██████╗ ███╗   ██╗
╚══██╔══╝██╔════╝██╔════╝██║  ██║    ╚══██╔══╝██║   ██║██╔════╝██╔════╝██╔═══██╗████╗  ██║
   ██║   █████╗  ██║     ███████║       ██║   ██║   ██║██║     ███████╗██║   ██║██╔██╗ ██║
   ██║   ██╔══╝  ██║     ██╔══██║       ██║   ██║   ██║██║     ╚════██║██║   ██║██║╚██╗██║
   ██║   ███████╗╚██████╗██║  ██║       ██║   ╚██████╔╝╚██████╗███████║╚██████╔╝██║ ╚████║
   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝       ╚═╝    ╚═════╝  ╚═════╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝

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








