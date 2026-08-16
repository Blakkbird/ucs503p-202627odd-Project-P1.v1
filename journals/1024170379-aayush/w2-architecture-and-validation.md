# Week 2 : System Architecture and Validation Strategy

During Week 2, I focused on understanding the proposed system architecture and how the performance of the forecasting system will be validated.

The project receives information from several sources. These include local PM2.5 observations, CAMS global forecasts, meteorological forecasts, and satellite fire detections. Each source provides different information that can potentially explain changes in local air quality.

I studied the overall flow of the system from data ingestion to prediction. The data is first collected and stored, after which the required features can be assembled into a modelling dataset. The correction model can then generate the next-day prediction, while the evaluation component compares the predictions with actual observations.

I paid particular attention to the evaluation strategy. A simple persistence forecast is used as an important baseline. This provides a reference against which the proposed correction method can be compared.

Since the data is time-dependent, I learned that a conventional random train-test split would not accurately represent the real forecasting situation. Future observations must not be allowed to influence a prediction made for an earlier date.

The proposal therefore uses rolling-origin backtesting. In this approach, the model is evaluated repeatedly at different points in time while ensuring that only information available before the prediction date is used.

I also understood the importance of preventing temporal leakage in the feature-building process. A feature should only be included if it would actually have been available when the forecast was supposed to be generated.

This week helped me understand how the architecture, data availability, and evaluation methodology are connected to the reliability of the final system.