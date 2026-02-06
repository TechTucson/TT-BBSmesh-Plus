# Let's now have the bot tell us Sunrise and Sunset Times. 
- We are going to build off of our last Enhancement.
- This will allow us to present Sunrise and Sunset Times to the user. 

### requirements.txt
- We'll need to add *suntime* to the requirements.txt file that way when we do our pip install we ensure all dependencies are accounted for. 

- 
### config.ini
- Let's scroll down to the utilities_menu_items and add N
- It should look something like this now:
  ```
  utilities_menu_items = S, F, W, X, T, N
   ```
- This will enable our new Menu Item
### command_handlers.py
- Let's start by adding at the very top of the document importing some libraries from suntime
  ```
  from suntime import Sun, SunTimeException
  ```
- Our build_menu needs some updating let's add :
  ```
        elif item.strip() == 'N':
            menu_str += "Su[N]\n"
  ```
- Now we need to create a function that will generate the needed output. We'll add this function:
  ```
  def handle_suntime_command(sender_id, interface):
    latitude = 33.4484
    longitude = 112.0740
    sun = Sun(latitude, longitude)
    today_sr = sun.get_sunrise_time()
    today_ss = sun.get_sunset_time()
    response_ss = "Sunrise and Sunset in Phoenix AZ WIll be Times in UTC"
    send_message(responsere_ss, sender_id, interface)
    send_message(str(today_sr) , sender_id, interface)
    send_message(str(today_ss) , sender_id, interface)
    ```


### message_processing.py
- We'll first add our *handle_suntime_command* to the command_handlers import section
  ``` from command_handlers import ( .....,handle_suntime_commnad)
  ```
- Now we'll add our menu item to the utilities_menu handlers.
  ```
utilities_menu_handlers = {
    ....,
    "d": handle_suntime_command
}

# That's it

