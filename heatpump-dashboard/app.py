from pathlib import Path
import pandas as pd

import numpy as np
import shutil
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
import openmeteo_requests
import requests_cache
from retry_requests import retry
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
from ipyleaflet import Map, Marker
from shinywidgets import output_widget, render_widget
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from htmltools import HTML, div

sns.set_theme(style="white")

cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Load cities data
cities = pd.read_csv(Path("/Users/rudhibashambu/sp24_cs498e2e-mp01_rudhib2/.venv/heatpump-dashboard/data/cities.csv"), na_values="NA")
city_choices = cities["city_state"].tolist()

display = ui.output_text(id="display_latlong")

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            id="city_state",
            label="City",
            choices=city_choices,
            selected="Urbana, Illinois",
            multiple=False,
            selectize=False,
            width=None,
            size=None,
            remove_button=None,
            options=None,
        ),
        display,
        ui.input_date_range(
            "daterange",
            "Date range",
            start="2022-01-01",
            end="2024-01-01",
            min="2020-01-01",
            max="2024-01-01",
        ),  # Added date range input
        ui.input_radio_buttons(
            "temp_unit",
            "Temperature Unit",
            ["Fahrenheit", "Celsius"],
            selected="Fahrenheit",
        ),
        ui.input_slider(  # Add a slider for temperature threshold
            "temp_threshold",
            "Plot Temperature",
            min=-15,
            max=50,
            value=5,
            step=1,
            width="100%",
        ),
        ui.input_checkbox_group(  # Add checklist for rolling averages
            id="rolling_avg",
            label="Plot Options",
            choices=["Weekly Rolling Average", "Monthly Rolling Average"],
            inline=True,
        ),
        ui.input_slider(  # Add a slider for temperature threshold
            "table_temp",
            "Table Temperatures",
            min=-25,
            max=60,
            value=[0, 15],
            step=1,
            width="100%",
        ),
        ui.page_fluid(output_widget("map")),
        ui.output_text(id="lng"),  # Added output_text for longitude
        ui.output_text(id="lat"),  # Added output_text for latitude
    ),
    ui.navset_underline(
        ui.nav_panel(
            "Historical",
            ui.output_plot("temp_date"),
            ui.output_text("temperature_range"),  # Added output text
            ui.card(
                ui.output_data_frame("temp_table_display_output"),
                full_screen=True,
                height="800px",
            ),
        ),
        ui.nav_panel(
            "About",
            div(
                HTML(
                    """
<p>Welcome to the Daily Heat Pump Efficiency Counter app! This application is designed to empower users with insights into daily temperature variations and their impact on heat pump performance.</p>

<h2>Features:</h2>

<ol>
  <li><b>City Selection:</b> Choose from a wide range of cities worldwide to explore local temperature trends.</li>
  <li><b>Date Range Selection:</b> Specify your desired date range to analyze historical temperature data.</li>
  <li><b>Temperature Units:</b> Toggle between Fahrenheit and Celsius to view temperatures in your preferred units.</li>
  <li><b>Temperature Thresholds:</b> Set a temperature threshold to highlight days where temperatures fall above or below your specified limit.</li>
  <li><b>Historical Data Visualization:</b> Visualize daily minimum temperatures using interactive scatter plots. Easily identify trends and anomalies in your selected city's climate.</li>
  <li><b>Rolling Averages:</b> Gain deeper insights into temperature trends by overlaying weekly or monthly rolling averages on the plots.</li>
  <li><b>Temperature Statistics:</b> Dive into detailed statistics with a table presenting the number of days and proportion of days below various temperature thresholds.</li>
  <li><b>Geographical Information:</b> Explore the geographical coordinates of your selected city, including latitude and longitude.</li>
  <li><b>Interactive Map:</b> Navigate the map to pinpoint the precise location of your chosen city. A marker on the map highlights the city's position for easy reference.</li>
</ol>

<h2>How to Use:</h2>

<ol>
  <li><b>Select City:</b> Choose your desired city from the dropdown menu. The app supports a wide range of cities globally.</li>
  <li><b>Choose Date Range:</b> Specify the start and end dates for the historical temperature data you wish to analyze.</li>
  <li><b>Select Temperature Unit:</b> Toggle between Fahrenheit and Celsius based on your preference.</li>
  <li><b>Set Temperature Threshold:</b> Define a temperature threshold to highlight temperature deviations from your desired range.</li>
  <li><b>Visualize Data:</b> Explore historical temperature data through interactive scatter plots, with options to include rolling averages.</li>
  <li><b>Analyze Statistics:</b> Review detailed statistics in the table view, providing insights into temperature distribution over the selected date range.</li>
  <li><b>Explore Geography:</b> Discover the geographical coordinates of your selected city, enhancing your understanding of its climate.</li>
  <li><b>Interact with Map:</b> Navigate the interactive map to visualize the precise location of your chosen city.</li>
</ol>
"""
                )
            ),
        ),
    ),
    title="Daily Heat Pump Efficiency Counter",
)


# Define server logic
def server(input: Inputs, output: Outputs, session: Session):
    @reactive.effect
    def _():
        # print("hi", input.temp_unit.get())
        if input.temp_unit() == "Fahrenheit":
            ui.update_slider("temp_threshold", min=-15, max=50, value=5)
            ui.update_slider("table_temp", min=-25, max=60, value=[0, 15])
        if input.temp_unit.get() == "Celsius":
            ui.update_slider("temp_threshold", min=-25, max=10, value=-15)
            ui.update_slider("table_temp", min=-30, max=15, value=[-20, -10])

    @reactive.calc
    def get_weather_data():
        city_state = (
            input.city_state.get()
        )  # Extract the actual value from the reactive object
        if city_state is None:
            return None  # Return None if no city state is selected

        lat = cities.loc[cities["city_state"] == city_state, "lat"].values
        lng = cities.loc[cities["city_state"] == city_state, "lng"].values
        if not lat or not lng:
            return None  # Return None if latitude or longitude is not found
        lat = lat[0]  # Access the first element directly
        lng = lng[0]  # Access the first element directly
        start_date = input.daterange()[0]  # Get start date from input
        end_date = input.daterange()[1]  # Get end date from input
        # temp_unit = "fahrenheit" if "Fahrenheit" in input.temp_unit.get() else "celsius"  # Determine temperature unit
        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_min",
            "temperature_unit": str(
                input.temp_unit()
            ).lower(),  # Use selected temperature unit
        }
        responses = openmeteo.weather_api(
            "https://archive-api.open-meteo.com/v1/archive", params=params
        )
        if not responses:
            return None
        return responses[0].Daily().Variables(0).ValuesAsNumpy()

    @reactive.calc
    def get_rolling_avg():
        rolling_avg = []
        data = get_weather_data()
        if data is None:
            return None
        data = pd.DataFrame(
            data, columns=["Temperature"]
        )  # Convert NumPy array to DataFrame
        data.index = pd.date_range(
            start=input.daterange()[0], periods=len(data), freq="D"
        )  # Set index to DatetimeIndex
        if "Weekly Rolling Average" in input.rolling_avg.get():
            weekly_avg = data["Temperature"].rolling(window=7).mean()
            rolling_avg.append(weekly_avg)
        if "Monthly Rolling Average" in input.rolling_avg.get():
            monthly_avg = data["Temperature"].rolling(window=30).mean()
            rolling_avg.append(monthly_avg)
        return rolling_avg

    @render.plot
    def temp_date():
        print("Input date range:", input.daterange())
        data = get_weather_data()
        if data is None:
            return None  # Return None if no data

        # Convert data to DataFrame with DatetimeIndex
        dates = pd.date_range(
            start=input.daterange()[0], end=input.daterange()[1], freq="D"
        )
        plot_data = pd.DataFrame({"Date": dates, "Temperature": data})

        # Create Matplotlib scatter plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Separate points below threshold
        below_threshold = plot_data[
            plot_data["Temperature"] < input.temp_threshold.get()
        ]
        above_threshold = plot_data[
            plot_data["Temperature"] >= input.temp_threshold.get()
        ]

        # Plot points below threshold in gray
        ax.scatter(
            below_threshold["Date"],
            below_threshold["Temperature"],
            marker="o",
            s=10,
            alpha=0.9,
            color="grey",
        )

        # Plot points above threshold in black
        ax.scatter(
            above_threshold["Date"],
            above_threshold["Temperature"],
            marker="o",
            s=10,
            alpha=0.9,
            color="black",
        )

        ax.set_ylabel(
            "Daily Minimum Temperature °" + input.temp_unit.get()[0]
        )  # Use selected temperature unit
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True)

        # Add horizontal line at selected temperature threshold
        temp_threshold = input.temp_threshold.get()
        ax.axhline(y=temp_threshold, color="grey", linestyle="-")
        ax.legend()

        daily_data = {}
        daily_data["temperature_2m_min"] = data

        daily_dataframe = pd.DataFrame(data=daily_data)
        daily_dataframe["rolling_average"] = (
            daily_dataframe["temperature_2m_min"]
            .rolling(window=7, min_periods=1)
            .mean()
        )

        daily_dataframe["rolling_average_monthly"] = (
            daily_dataframe["temperature_2m_min"]
            .rolling(window=30, min_periods=1)
            .mean()
        )

        print("input roll avg =", input.rolling_avg.get())
        if input.rolling_avg() == ("Weekly Rolling Average",):
            ax.plot(
                plot_data["Date"],
                daily_dataframe["rolling_average"],
                label="Weekly Rolling Average",
                linestyle="-",
                color="orange",
            )
        elif input.rolling_avg() == ("Monthly Rolling Average",):
            ax.plot(
                plot_data["Date"],
                daily_dataframe["rolling_average_monthly"],
                label="Monthly Rolling Average",
                linestyle="-",
                color="blue",
            )
        elif input.rolling_avg() == (
            "Weekly Rolling Average",
            "Monthly Rolling Average",
        ):
            ax.plot(
                plot_data["Date"],
                daily_dataframe["rolling_average"],
                label="Weekly Rolling Average",
                linestyle="-",
                color="orange",
            )
            ax.plot(
                plot_data["Date"],
                daily_dataframe["rolling_average_monthly"],
                label="Monthly Rolling Average",
                linestyle="-",
                color="blue",
            )

        ax.legend()

        return fig

    @reactive.calc
    def temp_table():
        # Calculate the temperature range based on the slider input
        return np.arange(input.table_temp()[0], input.table_temp()[1] + 1)

    @reactive.calc
    def days_below_temp():
        # Calculate the number of days below each temperature in the range
        data = get_weather_data()
        if data is None:
            return None

        below_threshold = data[data < input.table_temp()[1]]
        days_below = []
        for temp in temp_table():
            days_below.append(np.sum(below_threshold < temp))

        return days_below

    @reactive.calc
    def proportion_below_temp():
        # Calculate the proportion of days below each temperature in the range
        data = get_weather_data()
        if data is None:
            return None

        below_threshold = data[data < input.table_temp()[1]]
        total_days = len(data)
        proportion_below = [days / total_days for days in days_below_temp()]

        return proportion_below

    @output
    @render.data_frame
    def temp_table_display_output():
        # Create a DataFrame with temp, days below, and proportion below columns
        df = pd.DataFrame(
            {
                "Temp": temp_table(),
                "Days Below": days_below_temp(),
                "Proportion Below": proportion_below_temp(),
            }
        )

        # Sort the DataFrame by 'Temp' column in descending order
        df = df.sort_values(by="Temp", ascending=False)

        # Return the DataFrame directly
        return df

    @output
    @render.text
    def display_latlong():
        city_state = input.city_state.get()
        lat = cities.loc[cities["city_state"] == city_state, "lat"].values
        lng = cities.loc[cities["city_state"] == city_state, "lng"].values
        if not lat or not lng:
            return "Latitude and Longitude not available for selected city."

        # Extract the numerical values
        lat_value = lat[0]
        lng_value = lng[0]

        # Format the output
        output_text = f"{lat_value}°N, {lng_value}°E"

        return output_text

    @render_widget
    def map():
        city_state = input.city_state.get()
        lat = cities.loc[cities["city_state"] == city_state, "lat"].values
        lng = cities.loc[cities["city_state"] == city_state, "lng"].values
        if not lat or not lng:
            return "Latitude and Longitude not available for selected city."

        # Extract the numerical values
        lat_value = lat[0]
        lng_value = lng[0]

        # Create a map centered on the selected city's coordinates
        m = Map(center=(lat_value, lng_value), zoom=12)

        # Add a marker for the selected city
        marker = Marker(location=(lat_value, lng_value), draggable=False)
        m.add_layer(marker)

        return m

# Create the app
app = App(app_ui, server)

#test comment