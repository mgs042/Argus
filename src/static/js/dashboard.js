(function($) {
  'use strict';

  $.fn.andSelf = function() {
    return this.addBack.apply(this, arguments);
  }

  $(function() {
     // Function to get the current date and time in the desired format
     function getCurrentDateTime() {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, '0');
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = monthNames[now.getMonth()];
      const year = now.getFullYear();
      let hours = now.getHours();
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12; // The hour '0' should be '12'

      return `${day} ${month} ${year}, ${hours}:${minutes}${ampm}`;
    }


    // Function to create a dynamic alert card
    function createAlertCard(device, issue, severity, uid, isGW = false) {
      const cardLink = isGW ? 'gateway' : 'device'
      return `
        <div class="col-sm-4 grid-margin">
          <div class="card ${severity}" onclick="location.href='/${cardLink}?alert_uid=${uid}';">
            <div class="card-body">
              <div class="d-flex justify-content-end">
                <a href="/delete_alert?uid=${uid}">
                  <i class="icon-sm fa fa-window-close text-danger"></i>
                </a>
              </div>
              <h5>${device || gateway}</h5>
              <div class="d-flex d-sm-block d-md-flex align-items-center justify-content-between">
                <h3 class="mb-0">${issue}</h3>
                <div class="d-flex justify-content-end">
                  <i class="icon-lg fa fa-exclamation text-warning"></i>
                </div>
              </div>
            </div>
          </div>
        </div>`;
    }

    // Function to chunk the alerts into groups of 3
    function chunkAlerts(arr, size) {
      const result = [];
      for (let i = 0; i < arr.length; i += size) {
        result.push(arr.slice(i, i + size));
      }
      return result;
    }

    // Function to add rows to the container
    function addRowsToContainer(alertsData, containerId, isGW = false) {
      $(containerId).empty();  // Clear the container before adding new rows

      const chunkedAlerts = chunkAlerts(alertsData, 3);  // Chunk the alerts into groups of 3

      chunkedAlerts.forEach(chunk => {
        let rowHtml = '<div class="row">';  // Start a new row

        chunk.forEach(item => {
          if (isGW){
            const [device, issue, message, severity, uid] = item
            const cardHtml = createAlertCard(device, issue, severity, uid, isGW);  // Create the card HTML
            rowHtml += cardHtml;  // Add the card to the row
          }
          else{
            const [device, gateway, issue, message, severity, uid] = item;  // Unpack the tuple
            const cardHtml = createAlertCard(device, issue, severity, uid, isGW);  // Create the card HTML
            rowHtml += cardHtml;  // Add the card to the row
          }
        });

        rowHtml += '</div>';  // Close the row
        $(containerId).append(rowHtml);  // Append the row to the container
      });
    }
    // Store chart instances in a map (key: canvasId, value: chart instance)
    const chartInstances = new Map();
    // Doughnut Charts for device and gateway statuses
    function createDoughnutChart(canvasId, data) {
      const doughnutChartCanvas = document.getElementById(canvasId);

      // Check if there is an existing chart instance for this canvasId
      if (chartInstances.has(canvasId)) {
        const existingChart = chartInstances.get(canvasId);
        existingChart.destroy(); // Destroy the existing chart
        chartInstances.delete(canvasId); // Remove the reference from the map
      }

      // Create a new chart instance
      const newChart = new Chart(doughnutChartCanvas, {
        type: 'doughnut',
        data: {
          labels: ["Offline", "Online", "Never Seen"],
          datasets: [{
            data: data,
            backgroundColor: [
              "#cc0000", // Muted Red
              "#008000", // Dark Green
              "#ff8c00"  // Dark Orange
            ],
            borderColor: "#191c24"
          }]
        },
        options: {
          cutout: 70,
          animationEasing: "easeOutBounce",
          animateRotate: true,
          animateScale: false,
          responsive: true,
          maintainAspectRatio: true,
          showScale: false,
          plugins: {
            legend: {
              display: false,
            },
          },
        },
      });

      // Store the new chart instance in the map
      chartInstances.set(canvasId, newChart);
    }
   // Fetch data from the endpoints
   async function fetchData(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch data from ${url}:`, error);
      return [];
    }
  }
  function updateStatusAndAlerts() {
    // Fetch and dynamically populate Gateway Alerts
    fetchData('/gateway_alerts').then(gwAlerts => {
      if (gwAlerts && gwAlerts.length) {
        addRowsToContainer(gwAlerts, '#dynamic-rows1', true);
      }
    });

    // Fetch and dynamically populate Device Alerts
    fetchData('/device_alerts').then(alerts => {
      if (alerts && alerts.length) {
        addRowsToContainer(alerts, '#dynamic-rows2');
      }
    });

    // Fetch and dynamically create Doughnut Charts
    fetchData('/status_data').then(statusData => {
      if (statusData && statusData.devices && statusData.gateways) {
        createDoughnutChart('devices_donut', [
          statusData.devices.offline,
          statusData.devices.online,
          statusData.devices.never_seen
        ]);
        createDoughnutChart('gateways_donut', [
          statusData.gateways.offline,
          statusData.gateways.online,
          statusData.gateways.never_seen
        ]);
        $('.device_count').text(statusData.devices.total)
        $('.gateway_count').text(statusData.gateways.total)
        // Update datetime on page load
        $('#datetime1').text(getCurrentDateTime());
        $('#datetime2').text(getCurrentDateTime());
      }
      
    });
  }
  updateStatusAndAlerts();
  setInterval(updateStatusAndAlerts, 300000)

  });

})(jQuery);
