
# Let's now have the bot give us definitions of words. 
- We are going to build off of our last Enhancement.
- Our but will ask for the Word you would like defined and then provide the definition. 


### requirements/.txt
- We'll use this JSON English Language Dictionary located here: https://github.com/matthewreagan/WebstersEnglishDictionary/blob/master/dictionary.json I've also placed a copy in /Tools/dictionary.json
  
### config.ini
- Let's scroll down to the utilities_menu_items and add D
- It should look something like this now:
  ```
  utilities_menu_items = S, F, W, X, T, N, D
   ```
- This will enable our new Menu Item

  
### command_handlers.py


- Let's start by adding at the very top of the document 
 ```
 import json
 ```

 - Let's add an entry to the def(build_menu) function that will conincide with our *T*. Place it in between anything you'd like for now. 
   ```
           elif item.strip() == 'D':
            menu_str += "[D]efine\n"
   ```
     - This allows the Menu item *D* to be added to the Menus.
- Now we'll need to create our two new functions to do what we want it to do. One wil lhandle the actual message and the other will handle the steps within the message. 
  ````
  def handle_channel_dictionary_command(sender_id, interface):
      response = "📚 DICTIONARY📚 Press P to send word"
      send_message(response, sender_id, interface)
      update_user_state(sender_id, {'command': 'CHANNEL_DICTIONARY', 'step': 1})
  
  
  def handle_channel_dictionary_steps(sender_id, message, step, state, interface):
      message = message.lower().strip()
      if len(message) == 2 and message[1] == 'x':
          message = message[0]
  
      if step == 1:
          choice = message
          if choice == 'x':
              response = "From Within Dictionary Block"
              send_message(response, sender_id, interface)
              return
          elif choice == 'p':
              send_message("Send the word you want to define:", sender_id, interface)
              update_user_state(sender_id, {'command': 'CHANNEL_DICTIONARY', 'step': 3})
  
      elif step == 2:
          channel_index = int(message)
          channels = get_channels()
          if 0 <= channel_index < len(channels):
              channel_name, channel_url = channels[channel_index]
              send_message(f"Channel Name: {channel_name}\nChannel URL:\n{channel_url}", sender_id, interface)
          handle_channel_dictionary_command(sender_id, interface)
  
      elif step == 3:
          word = message
          with open('dictionary.json', 'r') as file:
             data = json.load(file)
          output = (data[word])
          lenght = (str(len(output)))
          #output2 = output[:output.index("2")]  
          output1 = output[:50]  
          output2 = output[50:100]          
          #send_message(word, sender_id, interface)
          send_message(output2, sender_id, interface)
          send_message("The Lenght is" + lenght, sender_id, interface)
          send_message(output1, sender_id, interface)
          send_message(output2, sender_id, interface)
          
  
  
  ```

### message_processing.py
- Next is to add the function we defined into the message_processing.py, to do this we'll tack on the that import task *from command_handlers import ()* and add our two functions
  ```
  from command_handlers import (.....,handle_channel_dictionary_command, handle_channel_dictionary_steps)
  ```
- Under the utilties_menu_handlers we'll also want to add our *d*.
  ```
  utilities_menu_handlers = {
  ....
  "d": handle_dictionary_command
  }
  ```
 - Find a place to throw this in, 
```
 elif command == 'CHANNEL_DICTIONARY':
                   handle_channel_dictionary_steps(sender_id, message, step, state, interface)
```
   - You can throw if after the Channel-Directory elif
     ```
                     elif command == 'CHANNEL_DIRECTORY':
                    handle_channel_directory_steps(sender_id, message, step, state, interface)
                elif command == 'CHANNEL_DICTIONARY':
                   handle_channel_dictionary_steps(sender_id, message, step, state, interface)
     ```   


# That's it

