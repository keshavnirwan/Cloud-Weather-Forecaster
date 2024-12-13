import streamlit as st
import hashlib
import json
import os
import requests
import cohere
from datetime import datetime

# Initialize the Cohere client
cohere_client = cohere.Client('uG2UTtCStEOSwS8YYphxmMatu3sbEoNb5BnXfWvu')


# Display the image (replace with your actual path)
st.image('Image2.jpg', width=250)

# Path to store users' data
USER_DATA_FILE = "users.json"

# Function to hash passwords using SHA256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to check if the user exists in the JSON file
def user_exists(username):
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            users = json.load(f)
            return username in users
    return False

# Function to register a new user
def register_user(username, password):
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "w") as f:
            json.dump({}, f)
    
    with open(USER_DATA_FILE, "r") as f:
        users = json.load(f)

    if username in users:
        return False  # User already exists

    users[username] = hash_password(password)
    
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)

    return True

# Function to authenticate an existing user
def authenticate_user(username, password):
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            users = json.load(f)
            if username in users and users[username] == hash_password(password):
                return True
    return False

# Login page
def login_page():
    st.title("Login Page")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["page"] = "weather"
            st.success(f"Welcome, {username}!")
            st.rerun()  # Refresh to redirect to the weather page
        else:
            st.error("Invalid username or password")

# Registration page
def register_page():
    st.title("Register New User")
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match")
        elif user_exists(username):
            st.error("User already exists")
        else:
            if register_user(username, password):
                st.success("Registration successful! You can now log in.")
                st.session_state["page"] = "login"
                st.rerun()  # Redirect to login after successful registration
            else:
                st.error("Error registering user. Please try again.")

# Weather function to fetch current and 5-day forecast data
def get_weather(city, date=None):
    api_key =  "25b5203749e95de7070452b2b9b844bc"  # Replace with your actual API key
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    forecast_url = "http://api.openweathermap.org/data/2.5/forecast?"

    # Get current weather
    complete_url = f"{base_url}q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(complete_url)
        data = response.json()

        if data["cod"] == "404":
            st.error("City not found!")
        else:
            main_data = data["main"]
            wind_data = data["wind"]
            weather_data = data["weather"][0]
            
            temperature = main_data["temp"]
            humidity = main_data["humidity"]
            wind_speed = wind_data["speed"]
            description = weather_data["description"]
            icon = weather_data["icon"]
            
            st.write(f"### Current Weather in {city}")
            st.metric("Temperature", f"{temperature} °C")
            st.metric("Humidity", f"{humidity} %")
            st.metric("Wind Speed", f"{wind_speed} m/s")
            st.write(f"*Description*: {description.capitalize()}")
            
            icon_url = f"http://openweathermap.org/img/wn/{icon}.png"
            st.image(icon_url, width=100)

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching weather data: {e}")

    # Get 5-day weather forecast
    try:
        forecast_complete_url = f"{forecast_url}q={city}&appid={api_key}&units=metric"
        forecast_response = requests.get(forecast_complete_url)
        forecast_data = forecast_response.json()
        
        if forecast_data["cod"] != "200":
            st.error("Could not fetch forecast data.")
        else:
            st.write(f"### 5-Day Weather Forecast for {city}")
            for day_data in forecast_data["list"][::8]:  # Get the data for 12:00 PM for each day
                date = day_data["dt_txt"]
                temperature = day_data["main"]["temp"]
                humidity = day_data["main"]["humidity"]
                description = day_data["weather"][0]["description"]
                wind_speed = day_data["wind"]["speed"]
                icon = day_data["weather"][0]["icon"]
                
                # Display each day's weather
                st.write(f"#### {date}")
                st.metric("Temperature", f"{temperature} °C")
                st.metric("Humidity", f"{humidity} %")
                st.metric("Wind Speed", f"{wind_speed} m/s")
                st.write(f"*Description*: {description.capitalize()}")
                
                icon_url = f"http://openweathermap.org/img/wn/{icon}.png"
                st.image(icon_url, width=50)

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching forecast data: {e}")

# Function to display and manage recent searches
def display_recent_searches():
    if "recent_searches" not in st.session_state:
        st.session_state["recent_searches"] = []
    
    # Display recent searches in the sidebar
    st.sidebar.title("Recent Searches")
    
    # Add a new search to the recent searches list if not already present
    city = st.session_state.get("current_city", "")
    if city and city not in st.session_state["recent_searches"]:
        st.session_state["recent_searches"].append(city)
    
    for idx, recent_city in enumerate(reversed(st.session_state["recent_searches"])):
        if st.sidebar.button(recent_city, key=f"recent_{idx}"):

            st.session_state["current_city"] = recent_city
            get_weather(recent_city)

# Function to interact with the Cohere chatbot
def interact_with_cohere(query):
    try:
        # Use Cohere to generate a response based on the user's input
        response = cohere_client.generate(
            model="command-xlarge",  # Model ID for Cohere's large model
            prompt=query,
            max_tokens=150  # Limit the number of tokens (characters) for the response
        )
        return response.generations[0].text.strip()  # Return the generated text response
    except Exception as e:
        return f"Error interacting with Cohere API: {e}"

# Main function to control page flow
def main():
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "page" not in st.session_state:
        st.session_state["page"] = "login"  # Default to the login page

    # Page navigation after authentication
    if st.session_state["authenticated"]:
        if st.session_state["page"] == "weather":
            st.title("Weather Forecasting")
            st.write("Welcome to the Weather Forecasting App!")

            # Calendar (date input) after authentication
            selected_date = st.date_input("Select a Date for Weather", datetime.today())

            # Get the current city from the session state or prompt for a new one
            city = st.text_input("Enter City Name", key="main_city_input")
            if city:
                st.session_state["current_city"] = city
                get_weather(city)

            # Display recent searches in the sidebar
            display_recent_searches()

            # Cohere Chatbot interaction
            st.title("Ask me!")
            user_query = st.text_input("Ask me anything!")
            if user_query:
                bot_response = interact_with_cohere(user_query)
                st.write(f"*Response:* {bot_response}")

            if st.button("Logout"):
                st.session_state["authenticated"] = False
                st.session_state["page"] = "login"
                st.rerun()  # Refresh after logout

    else:
        # Page navigation between login and register
        if st.session_state["page"] == "login":
            login_page()
            st.write("Don't have an account? [Register here](#).")
            if st.button("Go to Register Page"):
                st.session_state["page"] = "register"
                st.rerun()
        elif st.session_state["page"] == "register":
            register_page()
            if st.button("Back to Login"):
                st.session_state["page"] = "login"
                st.rerun()

if __name__ == "__main__":
    main()
