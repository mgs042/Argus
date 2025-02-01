(function () {
    'use strict';

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

    function updateStatusElement(elementId, status, details) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.innerHTML = `<span class="${status === false ? 'value text-danger' : 'value text-success'}">${details}</span>`;
    }

    function displayConfigData(chirpstack_status, influxdb_status, rabbitmq_status, telegram_status) {
        // Update ChirpStack status
        updateStatusElement('chirpstack_server_status', chirpstack_status.server_health.reachable, chirpstack_status.server_health.details);
        updateStatusElement('chirpstack_api_status', chirpstack_status.api_key_valid.valid, chirpstack_status.api_key_valid.details);

        // Update InfluxDB status
        updateStatusElement('influxdb_server_status', influxdb_status.server_health.reachable, influxdb_status.server_health.details);
        updateStatusElement('influxdb_token_status', influxdb_status.auth_valid.valid, influxdb_status.auth_valid.details);
        updateStatusElement('influxdb_org_status', influxdb_status.org_valid.valid, influxdb_status.org_valid.details);
        updateStatusElement('influxdb_bucket_status', influxdb_status.bucket_valid.valid, influxdb_status.bucket_valid.details);

        // Update RabbitMQ status
        updateStatusElement('rabbitmq_server_status', rabbitmq_status.server_health.reachable, rabbitmq_status.server_health.details);

        // Update Telegram status
        updateStatusElement('telegram_conn_status', telegram_status.validity, telegram_status.details);
    }

    async function checkConfig() {
        // Show loading state
        const button = document.getElementById('config-check-button');
        button.disabled = true;
        button.textContent = 'Checking...';

        try {
            const configData = await fetchData('/config_check');
            const [chirpstack_status, influxdb_status, rabbitmq_status, telegram_status] = configData;
            displayConfigData(chirpstack_status, influxdb_status, rabbitmq_status, telegram_status);
        } catch (error) {
            console.error('Failed to check configuration:', error);
            alert('Failed to check configuration. Please try again.');
        } finally {
            // Reset button state
            button.disabled = false;
            button.textContent = 'Check Configuration';
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const button = document.getElementById('config-check-button');
        if (button) {
            button.addEventListener('click', checkConfig);
        }
    });
})();