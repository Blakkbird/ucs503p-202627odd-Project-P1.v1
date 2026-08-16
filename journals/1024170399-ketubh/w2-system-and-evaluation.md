# Week 2 : Understanding the Data Sources and Evaluation Approach

During Week 2, I focused on understanding the different data sources and the proposed forecasting and evaluation workflow of Pawan.

The project combines multiple sources of information rather than depending only on the global CAMS forecast. The major inputs include local PM2.5 observations from the monitoring station, CAMS forecast data, meteorological forecasts, and satellite-based fire detections from relevant upwind regions.

I studied how these sources will eventually pass through the data pipeline. The general workflow consists of collecting the required data, storing the observations, preparing a common feature dataset, generating a next-day prediction, and evaluating the prediction against historical observations.

An important part of the project that I studied was the use of persistence as a baseline. Persistence provides a simple reference prediction by assuming that the next day's air quality will remain similar to the current value. The proposed correction model should therefore demonstrate an improvement over this simple baseline.

I also learned why time-series forecasting requires special care during evaluation. Randomly dividing observations into training and testing sets can allow information from the future to influence the model. To avoid this, the proposal uses rolling-origin backtesting, where each prediction is evaluated using only information that would have been available at that point in time.

Another important issue is temporal leakage. Features that would only become available after the prediction time cannot be used when generating a next-day forecast.

This week gave me a better understanding of how the data pipeline and evaluation methodology will affect the reliability of the final forecasting system.