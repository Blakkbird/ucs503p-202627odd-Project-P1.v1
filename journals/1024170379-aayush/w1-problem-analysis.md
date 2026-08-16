# Week 1 : Problem Analysis and Project Scope

Week one was primarily spent understanding the problem that our project, Pawan, is intended to address.

The project focuses on next-day PM2.5 forecasting for Patiala. I studied the motivation behind improving existing air quality forecasts instead of attempting to build an entirely new atmospheric forecasting system.

One of the main limitations discussed in the proposal is the spatial resolution of global atmospheric models such as CAMS. A global model represents atmospheric conditions over comparatively large grid cells, whereas air quality at a particular monitoring station can be strongly influenced by local factors.

The project therefore uses the Model Town, Patiala monitoring station as the local reference point. Historical observations from the station can be used to determine how well the available forecasts represent the actual conditions in Patiala.

I also studied the overall scope of the project. The proposed system will combine an existing forecast with local observations and additional contextual information. The aim is to produce a corrected next-day prediction and evaluate whether this correction provides a measurable improvement.

From a software engineering perspective, I understood that reproducibility is an important requirement. The system should have a clear data pipeline and should be possible to run repeatedly using well-defined inputs and processing steps.

By the end of Week 1, I had a clearer understanding of the project's motivation, scope, and expected outcome.