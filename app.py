import os
import requests

from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Needed by Socket.IO for session encryption
socketio = SocketIO(app, cors_allowed_origins="*")

# Insert your OpenWeatherMap API key here
OPENWEATHER_API_KEY = "671fdaa031def78f82865cfb3174d352"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weather + WebSocket</title>
    <style>
       body { font-family: Arial, sans-serif; margin: 30px; }
       .container { max-width: 400px; margin: auto; }
       input { width: 80%; padding: 8px; margin-right: 5px; }
       button { padding: 8px; }
       .result { margin-top: 20px; }
       .chat-section {
         margin-top: 40px;
         background-color: #f5f5f5;
         padding: 15px;
         border-radius: 5px;
       }
       .chat-messages {
         margin-bottom: 10px;
         max-height: 200px;
         overflow-y: auto;
         border: 1px solid #ddd;
         padding: 10px;
         background-color: #fff;
         border-radius: 5px;
       }
    </style>
</head>
<body>
  <div class="container">
    <h1>Check the Weather</h1>
    <form method="GET" action="/">
      <input type="text" name="city" placeholder="Enter city name" />
      <button type="submit">Get Weather</button>
    </form>
    {% if weather_info %}
      <div class="result">
        <h2>Weather for {{ city }}</h2>
        <p>{{ weather_info }}</p>
      </div>
    {% endif %}

    <!-- Real-time Chat Section -->
    <div class="chat-section">
      <h2>Simple Chat</h2>
      <div class="chat-messages" id="chatMessages"></div>
      <input type="text" id="chatInput" placeholder="Enter chat message..." />
      <button onclick="sendChat()">Send</button>
    </div>
  </div>

  <!-- 1) Load the Socket.IO client library from CDN -->
  <script 
      src="https://cdn.socket.io/4.5.4/socket.io.min.js">
  </script>

  <!-- 2) Now your custom script that references `io()` -->
  <script>
    // Connect to the server's SocketIO
    var socket = io();

    // Debugging: Log when the socket connects
    socket.on('connect', function() {
        console.log('Connected to server with SID:', socket.id);
    });

    // Debugging: Log if there's a connection error
    socket.on('connect_error', function(error) {
        console.error('Connection Error:', error);
    });

    // Listen for 'chat_message' events from the server
    socket.on('chat_message', function(data) {
        // data is an object: {message: "Something..."}
        var chatBox = document.getElementById('chatMessages');
        var p = document.createElement('p');
        p.textContent = data.message; 
        chatBox.appendChild(p);

        // auto-scroll to bottom
        chatBox.scrollTop = chatBox.scrollHeight;
    });

    // Send chat message to the server
    function sendChat() {
        var input = document.getElementById('chatInput');
        var msg = input.value.trim();
        if (msg) {
            // Emit a 'chat_message' event with 'msg' as payload
            socket.emit('chat_message', { text: msg });
            input.value = '';
        }
    }
  </script>

</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    """
    Renders the page and, if a city is provided, fetches
    the weather from OpenWeatherMap.
    """
    city = request.args.get("city")
    weather_info = None

    if city:
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        try:
            resp = requests.get(base_url, params=params)
            data = resp.json()

            if resp.status_code == 200:
                main = data['weather'][0]['main']
                description = data['weather'][0]['description']
                temp = data['main']['temp']
                weather_info = f"{main} ({description}), {temp} °C"
            else:
                message = data.get("message", "Something went wrong.")
                weather_info = f"Error: {message}"
        except Exception as e:
            weather_info = f"Error: {str(e)}"

    return render_template_string(HTML_TEMPLATE, city=city, weather_info=weather_info)

@socketio.on('connect')
def handle_connect():
    print("A client connected with SID:", request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print("A client disconnected. SID was:", request.sid)

@socketio.on('chat_message')
def handle_chat_message(data):
    """
    When a client sends a 'chat_message' event, we broadcast
    it to all clients (including the sender).
    'data' is expected to be a dictionary, e.g., {'text': "hello!"}
    """
    msg_text = data.get('text', '')
    print("Received chat message:", msg_text)

    # Emit the event 'chat_message' to ALL clients in the default namespace
    emit(
        'chat_message',
        {'message': f"User {request.sid} says: {msg_text}"},
        broadcast=True
    )

if __name__ == "__main__":
    # Run with socketio.run for WebSockets support
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
