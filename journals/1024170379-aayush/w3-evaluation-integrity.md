# Week 3 : Evaluation Integrity and Persistence Baseline

This week the project proposal was presented and accepted. I focused on understanding the evaluation methodology and, in particular, the persistence baseline used for comparison.

The persistence baseline predicts the next day's air quality using a previous observation. However, the monitoring station has a publication delay, meaning that the most recent observation available at the time a forecast has to be issued may be several days old.

The team identified that the original persistence calculation used completed historical data and could therefore use an observation that would not actually have been available at forecast time. This would make the baseline unfairly strong.

The evaluation was therefore adjusted to distinguish between the theoretical persistence value and an operational persistence baseline using only information available at the forecast issue time.

This highlighted an important point for the project: a baseline is not only a mathematical formula; it also depends on the information that was actually available when the prediction had to be made.

This week improved my understanding of leakage, fair model comparison, and the importance of maintaining the same information constraints for both the model and its baselines.
