import os
import requests
from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Replace with your actual OpenWeatherMap API key
OPENWEATHER_API_KEY = "671fdaa031def78f82865cfb3174d352"

# In‑memory favorites list
favorite_cities = []

# Global temperature unit; "metric" (°C) or "imperial" (°F)
temp_unit = "metric"

@app.route("/")
def index():
    return render_template("index.html", temp_unit=temp_unit)

@app.route("/api/weather")
def api_weather():
    """
    Returns weather info as JSON. Accepts either a "city" parameter or
    "lat" and "lon" parameters (for auto‑detect).
    """
    city = request.args.get("city")
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    params = {"appid": OPENWEATHER_API_KEY, "units": temp_unit}
    if city:
        params["q"] = city
    elif lat and lon:
        params["lat"] = lat
        params["lon"] = lon
        city = "Your Location"
    else:
        return jsonify({"error": "No city or coordinates provided"}), 400

    try:
        resp = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params)
        data = resp.json()
        if resp.status_code == 200:
            main = data['weather'][0]['main']
            description = data['weather'][0]['description']
            temp = data['main']['temp']
            icon = data['weather'][0]['icon']
            return jsonify({
                "city": city,
                "weather_info": f"{main} ({description}), {temp} °{'F' if temp_unit=='imperial' else 'C'}",
                "weather_main": main,
                "icon": icon
            })
        else:
            message = data.get("message", "Something went wrong.")
            return jsonify({"error": message}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/forecast")
def api_forecast():
    """
    Returns a 5‑day forecast as JSON for a given city or coordinates.
    """
    city = request.args.get("city")
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    params = {"appid": OPENWEATHER_API_KEY, "units": temp_unit}
    if city:
        params["q"] = city
    elif lat and lon:
        params["lat"] = lat
        params["lon"] = lon
        city = "Your Location"
    else:
        return jsonify({"error": "No city or coordinates provided"}), 400

    try:
        resp = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=params)
        data = resp.json()
        if resp.status_code == 200:
            forecast_list = data.get("list", [])
            daily_data = []
            # Get roughly one reading per day (every 8 items)
            for i in range(0, len(forecast_list), 8):
                item = forecast_list[i]
                dt_txt = item.get("dt_txt", "")
                temp = item["main"]["temp"]
                day_label = dt_txt.split(" ")[0]
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

@app.route("/toggle_unit", methods=["POST"])
def toggle_unit():
    global temp_unit
    temp_unit = "imperial" if temp_unit == "metric" else "metric"
    # If AJAX request, return JSON; otherwise, redirect
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"temp_unit": temp_unit})
    return redirect(url_for("index"))

# Socket.IO event handlers for chat
@socketio.on('chat_message')
def handle_chat_message(data):
    msg_text = data.get('text', '')
    print("Received chat message:", msg_text)
    emit('chat_message', {'message': f"User {request.sid} says: {msg_text}"}, broadcast=True)
    # Simple bot response if message starts with "!bot"
    if msg_text.toLowerCase().startsWith("!bot"):
        emit('chat_message', {'message': "Bot: Remember to check the weather before heading out!"}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    print(f"A client connected with SID: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"A client disconnected. SID was: {request.sid}")

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
