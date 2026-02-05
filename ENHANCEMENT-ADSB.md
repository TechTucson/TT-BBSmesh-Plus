
# Let's now have the bot give us some ADSB Data. 
- So far we've been working with local/static data. We'll be introducing a live data source, while the data will be live it is still offline. We'll be using
  - Hardware
    - RTL-SDR USB Dongle
    - Antenna ( The one that comes with is is fine for a proof of concept)
  - Software
    - Dump 1090
      - https://github.com/gvanem/Dump1090
      - This software uses the RTL-SDR Dongle and Dumps ADSB Data :)     
    - ADSB Stats Logger
      - https://github.com/nfacha/adsb-stats-logger/
      - This software uses the output from Dump1090 Logs it and has some statistics around the data.
     
  - Initially, we'll build the data to play with it within our bot.  Initially, it will be a request/response type of scenario. If ( big If) I feel confident I may incorporate an if-then-else function here, where if an aircraft is within a certain mileage it will alert the meshtastic channel. I am not confident in my abilities so far yet, that's why I preface it with an If. 
## Section 1.0 ( ADSB Data)
Let's try to simpligy this.

  - We'll need DOcker
  - Linux
  - Plug In your RTL-SDR
  - Make sure you see this ```lsusb | grep -i rtl```
```

Run Docker Container

sudo docker run -d   --name readsb3   --device=/dev/bus/usb   -p 8090:8080   -p 30003:30003   -p 30005:30005   --restart unless-stopped   ghcr.io/wiedehopf/readsb:latest   --device-type rtlsdr  --write-json yes   --json-location /run/readsb   --write-json-every 1

I took a simpler route to get the datafeed. I am taking the logs from the docker container and parsing those with Python. COming soon.

https://github.com/TechTucson/TT-BBSmesh-Plus/blob/main/ADSBPArser.py
```

## Section 1.1 ( ADSB Data)
- 1 Install RTL-SDR Dongle and IT's drivers, while we won't be using SDRSharp it would be wise to get that up and running. (It will ensure you have your SDR dongle working)
  - 1.1 Plug Everything in 
- 2 Download and extract Dump1090
  - 2.1 Edit the batch file
    ```
    dump1090.exe --interactive --net
    ```
  - 2.2 Double click the bat file and  you should now get some output on the Command Prompt Looking window
  - 2.3 While we don't need the --interactive part it's easy to see something on the screen, we will use the --net function. --net will enable a local web server where you can visit and interact with a service even use a map. The specific functionality we are after is a JSON file created continuously, we'll use this file to feed our ADSB logger.  
- 3 Take a look at the website http
- 4 Let's setup adsb-stats logger
  - 4.1 Download and extract
  - 4.2 Create and Activate Python Virtual Environment
      ```
      python -m venv venv
      venv\Scripts\activate 
      ```
  - 4.3 Modify logger.py
      - As-is the adsb-stats-logger uses a local file which I didn't want to figure out how DUMP1090 generates it. DUMP1090's --net functionality exposes a JSON file we will use to feed our ADSB logger as mentioned above. The logger.py takes that JSON file exposed on your local web server through HTTP and adds data points to an SQLITE Database. 
    - 4.3.1 Modify show.py
      - 4.3.1.1 For our Proof of Concept we are focusing on the latest Aircraft seen to send out the message within BBMesh. When we run show.py we'll get data we need. 
  - 4.4 Move logger.py and search.py into the Meshtastic folder we have been using.
  - 4.5 Add requirements from adsb-stats-logger for Python over to our main project requirements.txt file



## Section 2 (Meshtsastic Bot)



### requirements/.txt

### config.ini

  
### command_handlers.py

### message_processing.py

# That's it

