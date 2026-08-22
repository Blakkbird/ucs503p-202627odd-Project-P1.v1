# Week 3 : Data Quality and Forecast Inputs

This week the project proposal was presented and accepted. I focused on understanding some of the data-quality issues affecting the forecasting pipeline.

One issue we reviewed was the treatment of wind direction. Wind direction is a circular quantity, so directly taking the arithmetic mean of angles can produce incorrect results near the 0°/360° boundary. For example, averaging 350° and 10° arithmetically gives 180°, even though the two directions are actually close to north.

The team addressed this by representing wind direction using its vector components before averaging and converting the result back into a bearing.

I also reviewed how the quality and availability of input data can affect the final forecast. A technically correct pipeline can still produce incorrect results if the input data is interpreted incorrectly.

This week helped me understand that validating the meaning and quality of the data is as important as validating the code that processes it.
