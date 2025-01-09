console.log(gatewayUid)

// Global label-to-color mapping
const labelColorMap = {};

// Function to generate shades of blue based on value
function generateBlueShade(value) {
// Map the value to a blue color intensity (higher value -> darker blue)
const intensity = Math.min(value * 25, 255); // Scaling for 0-5 range
if(intensity == 0)
{
    return `rgb(255, 255, 255)`; //for value 0
}
else{
    return `rgb(0, 0, ${intensity})`; // Shades of blue: lighter for lower values, darker for higher values
}

}

fetch(`/gateway_metrics?uid=${gatewayUid}`)
.then(response => response.json())
.then(data => {
    const chartData = [
        { id: "rxPackets", data: data.rxPackets },
        { id: "txPackets", data: data.txPackets },
        { id: "txPacketsPerFreq", data: data.txPacketsPerFreq },
        { id: "rxPacketsPerFreq", data: data.rxPacketsPerFreq },
        { id: "txPacketsPerDr", data: data.txPacketsPerDr },
        { id: "rxPacketsPerDr", data: data.rxPacketsPerDr },
        { id: "txPacketsPerStatus", data: data.txPacketsPerStatus }
    ];

    chartData.forEach(chart => {
        const container = document.getElementById(chart.id);

        if (chart.data.datasets && chart.data.datasets.length > 0) {
            const isFreqChart = ['txPacketsPerFreq', 'rxPacketsPerFreq'].includes(chart.id);
            const isDRChart = ['txPacketsPerDr', 'rxPacketsPerDr'].includes(chart.id);
            const isStatusChart = ['txPacketsPerStatus'].includes(chart.id);
            const isLineChart = ['rxPackets', 'txPackets'].includes(chart.id);

            if (isFreqChart) {
                    // Sort datasets by label values (ascending order)
                chart.data.datasets.sort((a, b) => parseInt(a.label, 10) - parseInt(b.label, 10));

                // Stacked Bar Chart for freq and dr
                const traces = chart.data.datasets.map(dataset => {
                    return {
                        x: chart.data.timestamps,
                        y: dataset.data,
                        type: 'bar',
                        name: dataset.label
                    };
                });

                const layout = {
                    title: chart.data.name,
                    plot_bgcolor: 'rgba(160, 160, 160, 0.8)',
                    paper_bgcolor: 'rgba(255, 179, 179, 0.81)',

                    barmode: 'stack',
                    xaxis: {
                        title: 'Time',
                        type: 'date',
                        tickformat: "%H:%M",
                        dtick: 60 * 60 * 1000
                    },
                    yaxis: {
                        title: isFreqChart ? 'Frequency' : 'Data Rate',
                        tickvals: chart.data.datasets.map(ds => parseInt(ds.label, 10)),
                        ticktext: chart.data.datasets.map(ds => ds.label),
                    }
                };

                Plotly.newPlot(chart.id, traces, layout, {displayModeBar: false});

            }  else if (isDRChart) {
            
                    // Sort datasets by label values (ascending order)
                chart.data.datasets.sort((a, b) => parseInt(a.label, 10) - parseInt(b.label, 10));

                // Stacked Bar Chart for DR charts
                const traces = chart.data.datasets.map(dataset => {
                    // Apply the generateBlueShade only for DR charts
                    const color = generateBlueShade(parseInt(dataset.label, 10));

                    // Store color in labelColorMap to ensure consistent color for each label
                    if (!labelColorMap[dataset.label]) {
                        labelColorMap[dataset.label] = color;
                    }

                return {
                    x: chart.data.timestamps,
                    y: dataset.data,
                    type: 'bar',
                    name: dataset.label,
                    marker: { color: color }
                };
            });

            const layout = {
                title: chart.data.name,
                plot_bgcolor: 'rgba(160, 160, 160, 0.8)',
                paper_bgcolor: 'rgba(255, 255, 179, 0.81)',
                barmode: 'stack',
                xaxis: {
                    title: 'Time',
                    type: 'date',
                    tickformat: "%H:%M",
                    dtick: 60 * 60 * 1000
                },
                yaxis: {
                    title: 'Data Rate',
                    tickvals: chart.data.datasets.map(ds => parseInt(ds.label, 10)),
                    ticktext: chart.data.datasets.map(ds => ds.label),
                }
            };

            Plotly.newPlot(chart.id, traces, layout, {displayModeBar: false});
        }
                else if (isLineChart) {
                // Line Chart for rx and tx packets
                const trace = {
                    x: chart.data.timestamps,
                    y: chart.data.datasets[0].data,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: chart.data.datasets[0].label
                };

                const layout = {
                    title: chart.data.name,
                    plot_bgcolor: 'rgba(160, 160, 160, 0.8)',
                    paper_bgcolor: 'rgba(179, 255, 209, 0.81)',
                    xaxis: {
                        title: 'Time',
                        type: 'date',
                        tickformat: "%H:%M",
                        dtick: 60 * 60 * 1000
                    },
                    yaxis: {
                        title: 'Count'
                    }
                };

                Plotly.newPlot(chart.id, [trace], layout, {displayModeBar: false});

            } else if (isStatusChart) {
                // Normal Bar Chart for status
                const traces = chart.data.datasets.map(dataset => ({
                    x: chart.data.timestamps,
                    y: dataset.data,
                    type: 'bar',
                    name: dataset.label
                }));

                const layout = {
                    title: chart.data.name,
                    plot_bgcolor: 'rgba(160, 160, 160, 0.8)',
                    paper_bgcolor: 'rgba(187, 179, 255, 0.81)',
                    xaxis: {
                        title: 'Time',
                        type: 'date',
                        tickformat: "%H:%M",
                        dtick: 60 * 60 * 1000
                    },
                    yaxis: { title: 'Count' }
                };

                Plotly.newPlot(chart.id, traces, layout, {displayModeBar: false});
            }
        }
        else {
            container.innerHTML = `<div style="display: flex; justify-content: center; align-items: center; height: 100%; font-size: 1.0em;">
                                    No data available for ${chart.data.name}
                                </div>`;
        }
    });
})
.catch(error => {
    console.error('Error fetching metrics:', error);
});