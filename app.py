import os
import requests
from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Replace with your actual OpenWeatherMap API key
OPENWEATHER_API_KEY = "671fdaa031def78f82865cfb3174d352"

# In-memory favorites list
favorite_cities = []

# Global temperature unit; "metric" (°C) or "imperial" (°F)
temp_unit = "metric"


@app.route("/")
def index():
    return render_template("index.html", temp_unit=temp_unit)


@app.route("/api/weather")
def api_weather():
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
            sunrise = data['sys']['sunrise']
            sunset = data['sys']['sunset']
            return jsonify({
                "city": city,
                "weather_info": f"{main} ({description}), {temp} °{'F' if temp_unit=='imperial' else 'C'}",
                "weather_main": main,
                "icon": icon,
                "sunrise": sunrise,
                "sunset": sunset,
            })
        else:
            message = data.get("message", "Something went wrong.")
            return jsonify({"error": message}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/forecast")
def api_forecast():
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


@app.route('/api/aqi')
def get_aqi():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "City is required"}), 400

    try:
        aqi_url = f"http://api.airvisual.com/v2/city"
        params = {
            "city": city,
            "key": AIRVISUAL_API_KEY
        }
        resp = requests.get(aqi_url, params=params)
        data = resp.json()

        if resp.status_code != 200 or "data" not in data:
            return jsonify({"error": data.get("message", "Failed to fetch AQI data.")}), 400

        aqi_data = data["data"]["current"]["pollution"]
        aqi = aqi_data["aqius"]
        description = "Good" if aqi <= 50 else "Moderate" if aqi <= 100 else "Unhealthy"

        return jsonify({"aqi": aqi, "description": description})

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
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"temp_unit": temp_unit})
    return redirect(url_for("index"))


@socketio.on('chat_message')
def handle_chat_message(data):
    msg_text = data.get('text', '')
    emit('chat_message', {'message': f"User {request.sid} says: {msg_text}"}, broadcast=True)
    if msg_text.lower().startswith("!bot"):
        emit('chat_message', {'message': "Bot: Remember to check the weather before heading out!"}, broadcast=True)


@app.route('/api/reverse_geocode', methods=['GET'])
def reverse_geocode():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    if not lat or not lon:
        return jsonify({"error": "Missing latitude or longitude"}), 400

    try:
        geocode_url = f"http://api.openweathermap.org/geo/1.0/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "limit": 1
        }
        resp = requests.get(geocode_url, params=params)
        if resp.status_code != 200:
            return jsonify({"error": "Failed to reverse geocode"}), 500
        data = resp.json()
        if len(data) == 0:
            return jsonify({"error": "No location found"}), 404

        city = data[0].get('name', "Unknown Location")
        return jsonify({"city": city}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
