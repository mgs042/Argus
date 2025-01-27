(function ($) {
  'use strict';

  $(function () {
    console.log('Alerts:', alerts);

    // Function to create a dynamic alert card
    function createAlertCard(device, gateway, issue, message, severity, uid) {
      return `
        <div class="col-6">
          <div class="card ${severity}">
            <div class="card-alert">
              <div class="d-flex justify-content-end">
                <a href="/delete_alert?uid=${uid}">
                  <i class="icon-sm fa fa-window-close text-danger"></i>
                </a>
              </div>
               <h3 class="mb-0">${issue}</h3>
             
              <div class="d-flex d-sm-block d-md-flex align-items-center justify-content-between">
                <h5><span class="alert-key">Name:</span> ${device}</h5>
                <div class="d-flex justify-content-end">
                  <i class="icon-lg fa fa-exclamation text-warning"></i>
                </div>
              </div>
              <div class="alert_g">
                <h5><span class="alert-key">Gateway:</span> ${gateway}</h5>
              </div>
              <h5>${message}</h5>
            </div>
          </div>
        </div>
      `;
    }

    // Function to chunk the alerts into groups of 3
    function chunkAlerts(arr, size) {
      const result = [];
      for (let i = 0; i < arr.length; i += size) {
        result.push(arr.slice(i, i + size));
      }
      return result;
    }

    // Function to create and add rows to the container
    function addRowsToContainer() {
      $('#dynamic-rows').empty(); // Clear the container before adding new rows

      // Check if alerts array is defined and not empty
      if (!alerts || alerts.length === 0) {
        $('#dynamic-rows').html('<p>No alerts available.</p>');
        return;
      }

      // Chunk the alerts into groups of 2
      const chunkedAlerts = chunkAlerts(alerts, 2);

      // Loop through the chunked alerts and create rows with 3 cards per row
      chunkedAlerts.forEach((chunk) => {
        let rowHtml = '<div class="row g-2">'; // Start a new row with gap utility

        // Loop through each item in the chunk and create a card
        chunk.forEach((item) => {
          const [device, gateway, issue, message, severity, uid] = item; // Unpack the tuple
          const cardHtml = createAlertCard(
            device,
            gateway,
            issue,
            message,
            severity,
            uid
          ); // Create the card HTML
          rowHtml += cardHtml; // Add the card to the row
        });

        rowHtml += '</div>'; // Close the row
        $('#dynamic-rows').append(rowHtml); // Append the row to the container
      });
    }

    // Call the function to add rows when the page loads or on some event
    addRowsToContainer(); // Add rows on page load
  });
})(jQuery);
