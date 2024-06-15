
# Multi-Threaded Robot Control Server

## Overview
This project implements a multi-threaded TCP/IP server to control automated robots navigating towards a central coordinate within a given system. The server guides multiple robots simultaneously, managing tasks such as authentication, obstacle navigation, message retrieval, and energy recharging. The solution focuses on handling multiple clients, ensuring communication integrity through a fully textual protocol, and robust handling of various operational errors.

## Features
- Multi-threaded or multiprocess handling of multiple client connections.
- Text-based communication protocol with detailed command and response structures.
- Authentication using pre-shared key pairs.
- Error management including syntax, logic, and authentication failures.
- Energy recharging and management for autonomous robotic operations.

## Technologies
- Language: Python
- TCP/IP for network communication

## Getting Started

### Prerequisites
- Python 3.x installed
- Access to a Linux environment

### Testing
This project includes a testing setup using a Tiny Core Linux virtual machine image and a pre-configured tester provided as part of the course requirements.

1. Download and set up VirtualBox.
2. Import the Tiny Core Linux image for testing.
3. Start the server on your host machine.
4. Run the tester inside the Tiny Core environment with the following command:
   ```bash
   tester <port_number> <host_address> [test_numbers]
   ```
   - `<port_number>`: The port number your server is listening on.
   - `<host_address>`: Typically, the gateway address of your host machine.
   - `[test_numbers]`: Optional specific test numbers to run.

Refer to the official VirtualBox documentation for more details on setup and configurations if you encounter any networking issues between the host and the virtual machine.

### Running the Server
To run the server, execute the Python script from the terminal:
```bash
python server.py
```

## Contributing
Contributions to this project are welcome! Please fork the repository, make your changes, and submit a pull request.

## Contact
For any queries regarding this project, please reach out via email at matus.gls.tkac@gmail.com
