import os
import requests
from flask import Flask, request, render_template_string
app = Flask(__name__)

# Insert your OpenWeatherMap API key here
# or load from an environment variable if you want to keep it private
OPENWEATHER_API_KEY = "671fdaa031def78f82865cfb3174d352"

# Simple HTML template in a string (for a small demo)
# In a real project, you might keep templates in a /templates folder
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weather App</title>
    <style>
       body { font-family: Arial, sans-serif; margin: 30px; }
       .container { max-width: 400px; margin: auto; }
       input { width: 80%; padding: 8px; }
       button { padding: 8px; }
       .result { margin-top: 20px; }
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
  </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    # If user submitted a city (via ?city=), handle it
    city = request.args.get("city")
    weather_info = None

    if city:
        # Call OpenWeatherMap API
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        try:
            resp = requests.get(base_url, params=params)
            data = resp.json()  # parse JSON

            if resp.status_code == 200:
                # Successfully got weather data
                main = data['weather'][0]['main']
                description = data['weather'][0]['description']
                temp = data['main']['temp']
                weather_info = f"{main} ({description}), {temp} °C"
            else:
                # If city not found or other error from API
                message = data.get("message", "Something went wrong.")
                weather_info = f"Error: {message}"
        except Exception as e:
            weather_info = f"Error: {str(e)}"

    # Render the page (with or without weather_info)
    return render_template_string(HTML_TEMPLATE, city=city, weather_info=weather_info)

if __name__ == "__main__":
    # Run locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
