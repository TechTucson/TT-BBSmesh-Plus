# Let's have the BOT give us it's current time


### requirements.txt
- I don't know if this specific one is needed but we'll add datetime to the requirements.txt

### config.ini
- Let's scroll down to the utilities_menu_items and add T
- It should look something like this now:
  ```
  utilities_menu_items = S, F, W, X, T
   ```
- This will enable our new Menu Item
### command_handlers.py
- Let's start by adding at the very top of the document 
   ```
   import datetime
   ```
 - Now let's add an entry to the def(build_menu) function that will conincide with our *T*. Place it in between anything you'd like for now. 
   ```
           elif item.strip() == 'T':
            menu_str += "[T]ime\n"
   ```
     - This allows the Menu item *T* to be added to the Menus. 
  - Now we'll need to create our own function to do what we want it to do.
    ```
    def handle_time_command(sender_id, interface, menu_name=None):
    now = datetime.datetime.now()
    send_message(now.strftime("%Y-%m-%d %H:%M:%S"), sender_id, interface)
    ```
    - This function defines the  *now* variable and assigns it a value using the DateTime library (I think that's what it is) that we imported. Followed by sending the message back to the user. There's some formatting but that's not important for now. 

### message_processing.py
- Next is to add the function we defined into the message_processing.py, to do this we'll tack on the that import task *from command_handlers import ()* and add our hanle_time_command function.
  ```
  from command_handlers import (.....,handle_time_command)
  ```
- Under the utilties_menu_handlers we'll also want to add out *t*.
  ```
  utilities_menu_handlers = {
  ....
  "t": handle_time_command
  }
  ```
    - This tells the BOT that if we get a message with the letter *t* we are to use the handle_time_command function that we imported.

# That's it


