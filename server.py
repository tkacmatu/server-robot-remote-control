import socket
import threading
import sys

# Map for Server messages
server_messages = {
    "SERVER_CONFIRMATION": "{:05d}\a\b",
    "SERVER_MOVE": "102 MOVE\a\b",
    "SERVER_TURN_LEFT": "103 TURN LEFT\a\b",
    "SERVER_TURN_RIGHT": "104 TURN RIGHT\a\b",
    "SERVER_PICK_UP": "105 GET MESSAGE\a\b",
    "SERVER_LOGOUT": "106 LOGOUT\a\b",
    "SERVER_KEY_REQUEST": "107 KEY REQUEST\a\b",
    "SERVER_OK": "200 OK\a\b",
    "SERVER_LOGIN_FAILED": "300 LOGIN FAILED\a\b",
    "SERVER_SYNTAX_ERROR": "301 SYNTAX ERROR\a\b",
    "SERVER_LOGIC_ERROR": "302 LOGIC ERROR\a\b",
    "SERVER_KEY_OUT_OF_RANGE_ERROR": "303 KEY OUT OF RANGE\a\b"
}

# Map for Client messages
client_messages = {
    "CLIENT_MESSAGE": "CLIENT_MESSAGE ",
    "CLIENT_RECHARGING": "RECHARGING"
}

# Five different keys
KEYS = [
    (23019, 32037),
    (32037, 29295),
    (18789, 13603),
    (16443, 29533),
    (18189, 21952),
]

# Receive message
def receive_message(conn, max_lenght, is_recharging=False):
    # Set timeout to 1 second or 5 seconds depending on whether we're recharging or not
    timeout = 5 if is_recharging else 1
    conn.settimeout(timeout)

    buffer = bytearray()
    prev_char = None
    char_count = 0
    is_message_ended = False
    flag = False

    while not is_message_ended:
        try:
            # Read 1 byte at a time
            data = conn.recv(1)

            # Check if no data was received (connection closed)
            if not data:
                print("Connection closed by remote end")
                return None

            # Convert byte to character and add to buffer
            char = data.decode()
            buffer.extend(data)
            
            # Check if current character is end sequence and previous character is "\a"
            if char == "\b" and prev_char == "\a":
                is_message_ended = True
            else:
                prev_char = char
                char_count += 1

            # Check for message length exceeding limit
            if len(buffer) > max_lenght:
                if buffer.startswith(b"RE"):
                    max_lenght = 12
                    flag = True
                else:
                    conn.sendall(server_messages["SERVER_SYNTAX_ERROR"].encode())
                    conn.close()
                    print(f"the lenght of message was too long, max is set on : {max_lenght}")
                    return None

        except socket.timeout:
            print("Timeout while receiving data")
            return None
            
    message = buffer.decode().strip().rstrip("\a\b")
    if not message:
        print("Empty message received")
        return None
    
    if flag == True or (len(message) == 10 and max_lenght !=80):
        if message == "RECHARGING":
            print("Robot is recharging, waiting...")
            return receive_message(conn, 12, True)
        
    if is_recharging:
        if message == "FULL POWER":
            print(f"Robot charged!")
            return receive_message(conn, 20)

    # Check for multiple messages
    messages = message.split("\a\b")
    if len(messages) > 1:
        print(f"Received {len(messages)} messages at once")
        return messages[0], "\a\b".join(messages[1:])

    return message

# Pick up message
def pickup_secret_message(conn, addr):
    # Send SERVER_PICK_UP message
    conn.sendall(server_messages["SERVER_PICK_UP"].encode())

    # Receive robot's response
    robot_response = receive_message(conn, 80)
    if not robot_response:
        print(f"Robot didnt receive complete message.")
        conn.close(
        )
        return

    # Check if the response is CLIENT_MESSAGE or CLIENT_RECHARGING
    if robot_response.startswith(client_messages["CLIENT_RECHARGING"]):
        print(f"Robot {addr} is recharging, cannot pick up the secret message")
        conn.sendall(server_messages["SERVER_LOGIC_ERROR"].encode())
        
    else:
        secret_message = robot_response.rstrip("\a\b")
        print(f"Robot {addr} picked up the secret message: {secret_message}")
        conn.sendall(server_messages["SERVER_LOGOUT"].encode())

# ASCII represntation of username + returns hash
def compute_hash(username):
    ascii_sum = sum(ord(char) for char in username)
    return (ascii_sum * 1000) % 65536

def handle_client(conn, addr):
    
    print(f"Robot {addr} connected")

    # Receive CLIENT_USERNAME
    username = receive_message(conn, 18)
    if not username:
        print("Failed to receive username")
        conn.close()
        return
    username = username.strip()
    print(f"Received username: {username}")
    
    
    # Check if the length of the username is more than 18 characters
    if len(username) > 18:
        print(f"Invalid username length from {addr}: {username}")
        conn.sendall(server_messages["SERVER_SYNTAX_ERROR"].encode())
        conn.close()
        return

    # Send SERVER_KEY_REQUEST
    conn.sendall(server_messages["SERVER_KEY_REQUEST"].encode())

    # Receive CLIENT_KEY_ID
    key_id_str = receive_message(conn, 5)
    if not key_id_str:
        print("Failed to receive key ID")
        conn.close()
        return
    try:
        key_id = int(key_id_str.strip())
    except ValueError:
        print(f"Invalid Key ID from {addr}: {key_id_str}")
        conn.sendall(server_messages["SERVER_SYNTAX_ERROR"].encode())
        conn.close()
        return

    # Verify Key ID
    if not 0 <= key_id < len(KEYS):
        print(f"Invalid Key ID from {addr}")
        conn.sendall(server_messages["SERVER_KEY_OUT_OF_RANGE_ERROR"].encode())
        conn.close()
        return

    server_key, client_key = KEYS[key_id]

    # Compute hashes
    username_hash = compute_hash(username)
    server_confirmation = (username_hash + server_key) % 65536
    expected_client_confirmation = (username_hash + client_key) % 65536

    # Send SERVER_CONFIRMATION
    conn.sendall(server_messages["SERVER_CONFIRMATION"].format(server_confirmation).encode())

    # Receive CLIENT_CONFIRMATION
    client_confirmation_str = receive_message(conn, 7)
    if not client_confirmation_str:
        print("Failed to receive client confirmation")
        conn.close()
        return

     # Check the lenght and space
    if len(client_confirmation_str) > 5 or ' ' in client_confirmation_str:
        print(f"Invalid client confirmation from {addr}: {client_confirmation_str}")
        conn.sendall(server_messages["SERVER_SYNTAX_ERROR"].encode())
        conn.close()
        return
    
    try:
        client_confirmation = int(client_confirmation_str.strip())
    except ValueError:
        print(f"Invalid client confirmation from {addr}: {client_confirmation_str}")
        conn.sendall(server_messages["SERVER_LOGIN_FAILED"].encode())
        conn.close()
        return

    # Check CLIENT_CONFIRMATION
    if client_confirmation == expected_client_confirmation:
        print(f"Robot {addr} authenticated")
        conn.sendall(server_messages["SERVER_OK"].encode())

        move_robot(conn, addr)
    else:
        print(f"Robot {addr} failed authentication")
        conn.sendall(server_messages["SERVER_LOGIN_FAILED"].encode())
        
    conn.close()

# Robot stunt move
def robot_stunt_move(conn, addr):
    # Turn right
    turn_right(conn)
    # Move forward
    move_forward(conn)

    # Turn left
    turn_left(conn)

    # Move forward twice
    move_forward(conn)
    move_forward(conn)

    # Turn left
    turn_left(conn)

    # Move forward
    cords = move_forward(conn)

    # Turn right
    turn_right(conn)
    
    if cords == (0,0):
        print(f"Robot {addr} reached (0,0)")
        pickup_secret_message(conn, addr)
        conn.close()
    print(f"Cords are : {cords}")
    
    return cords

# Rotate robot 180 degree
def robot_flip(conn):
    # Send two SERVER_TURN_LEFT messages
    conn.sendall(server_messages["SERVER_TURN_LEFT"].encode())
    client_ok_msg = receive_message(conn, 12)
    if client_ok_msg is None:
        print("Error: Did not receive OK message after first turn")
        return

    conn.sendall(server_messages["SERVER_TURN_LEFT"].encode())
    client_ok_msg = receive_message(conn, 12)
    if client_ok_msg is None:
        print("Error: Did not receive OK message after second turn")
        return

    print("Robot flipped twice to the left")

# Shows in what quartal robot is
def get_quartal(coords):
        if ((coords[0] > 0) and (coords[1] > 0)):
            return 1 #Up-right
        elif ((coords[0] < 0) and (coords[1] > 0)):
            return 2 #Up-left
        elif ((coords[0] < 0) and (coords[1] < 0)):
            return 3 #Down-left
        elif ((coords[0] > 0) and (coords[1] < 0)):
            return 4 #Down-right
        else:
            print("Invalid case")
           
# Turns right 
def turn_right(conn):
    conn.sendall(server_messages["SERVER_TURN_RIGHT"].encode())
    client_ok_msg = receive_message(conn, 12)
    if client_ok_msg is None:
        print("Error: Did not receive OK message after turning right")
        return
    client_ok_msg = client_ok_msg.strip().rstrip("\a\b")
    if not client_ok_msg.startswith("OK "):
        print(f"Error: Did not receive correct message in turn_right : {client_ok_msg}")

# Turns left
def turn_left(conn):
    conn.sendall(server_messages["SERVER_TURN_LEFT"].encode())
    client_ok_msg = receive_message(conn, 12)
    if client_ok_msg is None:
        print("Error: Did not receive OK message after turning left")
        return
    client_ok_msg = client_ok_msg.strip().rstrip("\a\b")
    if not client_ok_msg.startswith("OK "):
        print("Error on turning left in move_forward")

# Shows where is robot headed            
def find_direction(old, new):
    # Compare x and y coordinates to determine direction
    if old[0] == new[0] and old[1] < new[1]:
        return 2  # Left
    elif old[0] < new[0] and old[1] == new[1]:
        return 3  # Down
    elif old[0] == new[0] and old[1] > new[1]:
        return 0  # Up
    elif old[0] > new[0] and old[1] == new[1]:
        return 1  # Right
    else:
        print(f"Invalid direction \nold is {old}\nnew is {new}")
        return None
    
# Gets new direction    
def get_new_direction(position):
    if position[0] == 0:
        if position[1] < 0:
            return 0 #Up
        else:
            return 2 #Down
    elif position[1] == 0:
        if position [0] < 0:
            return 1 #Right
        else:
            return 3 #Left
    else: 
        print("Error while getting new direction.")
    
# Turns to direction    
def turn_to_desired_direction(conn, current, desired):
    while True:
        turn_right(conn)
        current = (current + 1) % 4
        if current == desired:
            break
        
# Switch        
def get_desired_direction2(quartal, direction):
    if quartal == 1:
        if direction == 2:
            desired_direction = 3
        else: 
            desired_direction = 2
    elif quartal == 2:
        if direction == 2:
            desired_direction = 1
        else: 
            desired_direction = 2
    elif quartal == 3:
        if direction == 0:
            desired_direction = 1
        else: 
            desired_direction = 0
    elif quartal == 4:
        if direction == 0:
            desired_direction = 3
        else: 
            desired_direction = 0
    return desired_direction
    
# Moving robot to the centre
def move_robot(conn, addr):
    
    #Presets the variables
    quartal = None
    X_on_zero = False
    Y_on_zero = False
    desired_direction = None

    # Determines the quartal and direction facing
    previous_pos = move_forward(conn)
    if previous_pos is None:
        print(f"Robot {addr} couldnt make first move")
        return
    current_pos = move_forward(conn)
    if current_pos is None:
        print(f"Robot {addr} couldnt make second move")
        return
    if (previous_pos != current_pos):
        if (current_pos[0] == 0 or current_pos[1] == 0):
            if current_pos[0] == 0:
                X_on_zero = True
            else: Y_on_zero = True
        else: 
            quartal = get_quartal(current_pos)
                
        direction = find_direction(current_pos, previous_pos)
    else: 
        print(f"pozicie : {previous_pos}  a {current_pos}")
        previous_pos = current_pos
        turn_right(conn)
        current_pos = move_forward(conn)
        if (current_pos[0] == 0 or current_pos[1] == 0):
            if current_pos[0] == 0:
                X_on_zero = True
            else: Y_on_zero = True
        else: 
            quartal = get_quartal(current_pos)
    
        # Gets dirrection and quartal ---------> doesnt have to be here but for now i didnt find better place
        direction = find_direction(current_pos, previous_pos)
        
    switch = False 
    while True:
        
            
        # If one axis is already done, the other will be finnished
        if (Y_on_zero or X_on_zero):
            desired_direction = get_new_direction(current_pos)
            if direction != desired_direction:
                turn_to_desired_direction(conn, direction, desired_direction)
            while True:
                
                #check if I am stuck
                if current_pos == previous_pos:
                    current_pos = robot_stunt_move(conn, addr)
                previous_pos = current_pos
                
                current_pos = move_forward(conn)
                
                if current_pos == (0,0):
                    print(f"Robot {addr} reached (0,0)")
                    pickup_secret_message(conn, addr)
                    return
            
        # Finds and turns into right direction    
        if switch == False:
            if quartal <= 2:
                desired_direction = 2
            else: 
                desired_direction = 0 
            if direction != desired_direction:
                    turn_to_desired_direction(conn, direction, desired_direction)
                    direction = desired_direction
                    
        if switch == True:
            desired_direction = get_desired_direction2(quartal, direction)
            turn_to_desired_direction(conn, direction, desired_direction)
            direction = desired_direction
            switch = False
               
        #check if I am stuck
        if current_pos == previous_pos:
            switch = True
        previous_pos = current_pos
        current_pos = move_forward(conn)
        
        if current_pos[0] == 0:
            X_on_zero = True
            print(f"X_on_zero = {X_on_zero}")
        elif current_pos[1] == 0:
            Y_on_zero = True
            print(f"Y_on_zero = {Y_on_zero}")
            
# Moves forward once and returns coords
def move_forward(conn):
    
    conn.sendall(server_messages["SERVER_MOVE"].encode())
    client_ok_msg = receive_message(conn, 12)
    if client_ok_msg is None:
        print(f"Error while receiving message in move_forward")
        conn.close()
        return None
        
    if client_ok_msg.endswith(" "):
        conn.sendall(server_messages["SERVER_SYNTAX_ERROR"].encode())
        conn.close() 
        return None

    if client_ok_msg.startswith("OK "):
        coords_str = client_ok_msg[3:]
        if coords_str[-1] == ' ':
            coords_str = coords_str[:-1]
        coords = coords_str.split(" ")

        if len(coords) == 2:
            try:
                x, y = int(coords[0]), int(coords[1])
            except ValueError:
                conn.sendall(server_messages["SERVER_SYNTAX_ERROR"].encode())
                conn.close()        
        return x, y
    return None

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("localhost", 12345))
    server.listen()

    print("Server started. Waiting for robots...")

    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
        except KeyboardInterrupt:
            print("\nThe server was stopped by the user.")
            sys.exit()

start_server()
