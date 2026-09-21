# BMS Screen Captures Automate

A Python tool to remotely capture screenshots of a PC, and send them directly to your LINE Messenger chat. Control the captures via simple chat commands.

This application uses a secure tunnel to expose a local web server, allowing the LINE Messaging API to communicate with the PC without requiring firewall configurations or a static public IP.

## Features

- **Remote Control via LINE**: Send commands from your phone to your PC.
- **On-Demand Captures**: Instantly capture the screen with a simple command.
- **Scheduled Captures**: Automate captures at regular intervals (e.g., every 10 minutes, 1 hour).
- **Custom Notes**: Add descriptive notes to both manual and scheduled captures for context.
- **Direct Image Delivery**: Screenshots are sent as images directly to your LINE chat.
- **Local Storage**: All captures are saved locally as optimized JPEGs in a `screenshots` folder.
- **Secure Tunneling**: Uses `Pinggy` to automatically create a secure HTTPS webhook for the LINE API.

## How It Works

1.  **Launcher (`launcher.py`)**: This is the main entry point. It starts two key background processes:
    -   A secure SSH tunnel using `Pinggy`, which generates a public URL (e.g., `https://your-tunnel.pinggy.io`).
    -   A local Flask web server (`server.py`) that listens for incoming connections.
2.  **Webhook Registration**: The launcher script automatically registers the public `Pinggy` URL with the LINE Messaging API as the webhook endpoint.
3.  **LINE Commands**: When you send a command (e.g., `capture`) to your LINE Bot, LINE sends a request to the public webhook URL.
4.  **Server (`server.py`)**: The Flask server receives the command, processes it, and triggers the appropriate action (e.g., taking a screenshot).
5.  **Capture (`capture.py`)**: The script captures the primary monitor's screen using `mss` and saves it as a compressed JPEG file in the `./screenshots` directory.
6.  **Image Serving**: The Flask server serves the saved image file from a local endpoint (e.g., `/images/shot_...jpg`).
7.  **Response (`line_api.py`)**: The application sends a message back to you via the LINE API, containing the image URL and any associated notes. LINE's servers then fetch the image from your public URL and display it in your chat.
8.  **Scheduler (`scheduler.py`)**: A background thread runs continuously, triggering captures automatically based on the schedule you set with the `start-capture` command.

## Setup and Installation

### Initial Setup & Credentials
For a complete, step-by-step walkthrough on creating your LINE Bot, generating the Channel Access Token, and locating your User ID, refer to the setup guide:

📄 **[LINE Bot Setup Guide (Google Docs)](https://docs.google.com/document/d/1oSsgUNEL6c992JcApr_k-gEb5fxM4gH7/edit?usp=sharing&ouid=104439298012117980509&rtpof=true&sd=true)**


## Usage

### Running the Application

To start the service, run the `launcher.py` script from your terminal:

```bash
python launcher.py
```

The terminal will display the startup sequence:
1.  Establishing the secure `Pinggy` tunnel.
2.  Starting the local Flask server.
3.  Registering the webhook with the LINE platform.

Once ready, you will receive a message in your LINE chat: "🟢 BMS Screen Capture Bot is ONLINE! PC connected and ready for commands."

Keep the terminal window running. To stop the application, press `Ctrl+C` in the terminal.

### LINE Commands

Send these commands as messages to your bot in the LINE app.

#### `capture [optional note]`

Takes an immediate screenshot and sends it to you. You can add a note for context.

**Examples:**
-   `capture`
-   `capture Chiller 1 pressure check`

#### `start-capture [interval] [optional note]`

Starts an automated, periodic capture session. The first capture is taken immediately.

-   **`[interval]`**: The time between captures. Use `s` for seconds, `m` for minutes, `h` for hours. If no unit is specified, it defaults to seconds. (e.g., `30s`, `10m`, `1h`, or `600`).
-   **`[optional note]`**: A recurring note that will be included with every scheduled capture.

**Examples:**
-   `start-capture 10m` (Captures every 10 minutes)
-   `start-capture 1h AHU-01 Performance`
-   `start-capture 900` (Captures every 900 seconds / 15 minutes)

#### `stop-capture`

Stops the currently running scheduled capture session.

**Example:**
-   `stop-capture`
