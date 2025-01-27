(function($) {
  'use strict';

  $.fn.andSelf = function() {
    return this.addBack.apply(this, arguments);
  }

  $(function() {

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
    console.log(gw_alerts)
    // Dynamically add alerts to containers
    if (gw_alerts && gw_alerts.length) {
      addRowsToContainer(gw_alerts, '#dynamic-rows1', true);  // Add Gateway Alerts to container
    }

    if (alerts && alerts.length) {
      addRowsToContainer(alerts, '#dynamic-rows2');  // Add Device Alerts to container
    }

    // Doughnut Charts for device and gateway statuses
    function createDoughnutChart(canvasId, data) {
      const doughnutChartCanvas = document.getElementById(canvasId);
      new Chart(doughnutChartCanvas, {
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
          legend: {
            display: false,
          },
          plugins: {
            legend: {
              display: false,
            },
          },
        },
      });
    }

    // Create charts for device and gateway statuses
    createDoughnutChart('devices_donut', [d_status.offline, d_status.online, d_status.never_seen]);
    createDoughnutChart('gateways_donut', [g_status.offline, g_status.online, g_status.never_seen]);

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

    // Update datetime on page load
    $('#datetime1').text(getCurrentDateTime());
    $('#datetime2').text(getCurrentDateTime());

  });

})(jQuery);
