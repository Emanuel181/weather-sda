import os
import requests
from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Needed by Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

OPENWEATHER_API_KEY = "671fdaa031def78f82865cfb3174d352"

# In-memory list of favorite cities for demonstration
favorite_cities = []

@app.route("/")
def index():
    """ Renders the main page: Weather + Chat + 5-Day forecast chart. """
    return render_template("index.html")

@app.route("/api/weather")
def api_weather():
    """
    Returns weather info as JSON for the given city (?city=...).
    """
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "No city provided"}), 400

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
            return jsonify({
                "city": city,
                "weather_info": f"{main} ({description}), {temp} °C"
            })
        else:
            message = data.get("message", "Something went wrong.")
            return jsonify({"error": message}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/forecast")
def api_forecast():
    """
    Returns a 5-day forecast for a city (?city=...).
    We'll parse the data to create something Chart.js can use.
    """
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "No city provided"}), 400

    base_url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    try:
        resp = requests.get(base_url, params=params)
        data = resp.json()
        if resp.status_code == 200:
            # parse forecast data
            forecast_list = data.get("list", [])

            daily_data = []
            # every 8 items ~ 1 day
            for i in range(0, len(forecast_list), 8):
                item = forecast_list[i]
                dt_txt = item.get("dt_txt", "")
                temp = item["main"]["temp"]
                day_label = dt_txt.split(" ")[0]  # "YYYY-MM-DD"
                daily_data.append({
                    "date": day_label,
                    "temp": temp
                })
                if len(daily_data) >= 5:
                    break

            return jsonify({
                "city": city,
                "forecast": daily_data
            })
        else:
            message = data.get("message", "Something went wrong.")
            return jsonify({"error": message}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_favorite", methods=["POST"])
def add_favorite():
    city = request.form.get("favorite_city")
    if city and city not in favorite_cities:
        favorite_cities.append(city)
    return redirect(url_for("show_favorites"))

@app.route("/favorites")
def show_favorites():
    return render_template("favorites.html", favorites=favorite_cities)

# ---------------------------
# Socket.IO Event Handlers
# ---------------------------
@socketio.on('connect')
def handle_connect():
    print(f"A client connected with SID: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"A client disconnected. SID was: {request.sid}")

@socketio.on('chat_message')
def handle_chat_message(data):
    msg_text = data.get('text', '')
    print("Received chat message:", msg_text)
    emit(
        'chat_message',
        {'message': f"User {request.sid} says: {msg_text}"},
        broadcast=True
    )

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
