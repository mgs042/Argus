<div align="center">
  <img src='/src/static/assets/images/eye.png' alt='Logo' style='width:100px; border-radius:50px;'>
  <img src="https://github.com/user-attachments/assets/929f6ab6-28d8-4da1-8184-565eba1d73c8" alt="Title">
</div>
<hr style='height: 5px;'>

**IoT Security Monitoring and Resource Management Tool**

![Demo-Video](https://github.com/user-attachments/assets/159942f1-8c06-447d-90e3-d1fcd870d263)


## **Overview**

**Argus** is an IoT security monitoring and resource management tool designed to integrate seamlessly with the **Chirpstack Application Server**. It collects event metrics, monitors network resources, stores relevant metrics in **InfluxDB**, and downsamples it with pre-defined Influx Tasks. Argus utilizes **Celery** workers for background task processing, including periodic **threat detection checks** and metric data processing. It can be deployed as Docker containers via Docker Compose for easy setup, scalability, and management.

### **Key Features:**

- **IoT Security Monitoring**: Detects and alerts on security threats such as:
    - **Packet Flooding**
    - **Join Request Replay**
    - **Frame Count Reset / Device Reset**
    - **Packet Loss**
    - **Active/Inactive Devices and Gateways**
    - **RF Jamming (RSSI and SNR threshold breach)**
    - **Link Margin Threshold Breach**
    - **Battery Status**
    - **Gateway Location Shift**
- **Resource Management**: Argus acts as a resource management system, keeping track of:
    - All IoT **devices** and **gateways** in the network.
    - **Device and Gateway status**, including active/inactive status and metrics.
    - **Resource usage** of the devices, ensuring efficient management.
- **Docker Compose Deployment**: Argus can be deployed as a set of Docker containers, making it easy to deploy and scale in a containerized environment. The containers include:
    - **Main Argus Server** (Handles API and communication)
    - **InfluxDB** (For storing metrics and logs)
    - **RabbitMQ** (For communication with Celery)
    - **Celery Beat** (For periodic tasks)
    - **Celery Workers** (For handling background tasks, scalable based on network traffic)
- **Scalability**: The Celery workers can be scaled up based on the traffic load and network size, allowing for high availability and better performance in large-scale networks.

---

## **Installation and Deployment**

Argus can be deployed using **Docker Compose** for easy management and scalability. Below are the steps to set up the system.

### **1. Clone the Repository**

Clone the repository to your local machine:

```bash
git clone https://github.com/mgs042/Argus.git
cd argus
```

### **2. Docker Compose Setup**

Argus uses **Docker Compose** to manage multiple containers. Follow the steps below to set it up:

1. **Ensure Docker and Docker Compose are installed** on your machine. You can install them using the following commands:
    - For Docker:
        
        ```bash
        sudo apt-get install docker-ce docker-ce-cli containerd.io
        ```
        
    - For Docker Compose:
        
        ```bash
        sudo apt-get install docker-compose
        ```
        
2. In the repository, you will find a `docker-compose.yml` file that defines the services for Argus and its components (Argus server, InfluxDB, RabbitMQ, Celery, etc.).
3. Edit the `config.py` file to set the correct configurations for your setup (e.g., database settings, RabbitMQ credentials).
4. **Start the Docker containers** using Docker Compose:
    
    ```bash
    docker-compose up -d
    ```
    
    This will start the following containers:
    
    - **argus**: The main server for the Argus application.
    - **influxdb2**: The database for storing metrics and logs.
    - **rabbitmq**: The messaging service used by Celery.
    - **celery-beat (or similar)**: The service that schedules periodic tasks.
    - **celery-worker (or similar)**: The workers that process background tasks.
5. Once the containers are up and running, you can access the **Argus web dashboard** at [`http://localhost:5000`](http://localhost:5000) and monitor the device status and network security.

    - **Default Username**: admin
    - **Defualt Password**: admin1234
6. Check if all the necessary components are up and running, and make changes to the configuration as necessary.
---
### **3. Scale Celery Workers**

The number of Celery workers can be scaled depending on the network traffic. To scale the number of Celery workers, use the following command:

```bash
docker-compose scale celery-worker=5
```

This will start 5 Celery worker containers. You can adjust the number based on the load and the size of the network.

---

## **Usage**

- **Monitor Network Resources**: Argus keeps track of all IoT devices and gateways in the network. It monitors device status, resource usage, and metrics, providing real-time insights into network health and security.
- **Threat Detection**: Argus continuously monitors for potential IoT security threats. When a threat is detected, alerts are generated, and corresponding actions are logged for further analysis.
- **Device Status Monitoring**: Argus integrates with the Chirpstack API to fetch device status (active or inactive) and track device metrics like frame count, packet loss, and more.
- **Alert Notifications**: When threats are detected or device status changes, Argus sends real-time notifications via the dashboard, email, or SMS. **(Work in Progress)**

---

## **Threat Detection Capabilities**

Argus is capable of detecting the following security threats:

- **Packet Flooding**: Argus detects unusual patterns of packet transmission that could indicate a denial-of-service (DoS) or packet flooding attack.
- **Join Request Replay**: Detects attempts to replay join requests in an unauthorized manner, often used for network infiltration.
- **Frame Count Reset/Device Reset**: Monitors for resets of frame counters or device resets, which could indicate tampering or attacks on device integrity.
- **Packet Loss**: Argus will soon monitor and alert for sudden or abnormal packet loss, indicating network instability or attack.
- **Active/Inactive Devices and Gateways**: Tracks whether gateways and devices are active or inactive in the network, ensuring that all components are properly monitored for security issues.
- **RF Jamming**: Monitors whether LoRa RF signals are not being jammed and ensures that the gateway receivers have a good signal strength and a signal-to-noise ratio to separate the original signal from the modulated carrier
- **Link Margin**: Monitors whether Signal strength is optimum for LoRa signals to be decoded, it should neither be too high (unecessary wastage of power) or too low (chances of information loss).
- **Battery Status**: Alerts when the battery level shown in the device status messages are too low.
- **Gateway Location Shift**: Keeps track of gateway locations and detects any location shifts.

---

## **Configuration**

The following configuration files can be modified to set up and customize Argus:

- **docker-compose.yml**: To configure the services and container options for Argus.
- **config.py**: For API credentials, InfluxDB configuration, Celery configuration, Chirpstack configuration etc..

---

## **Scaling and Performance**

As your network grows, Argus can be scaled to handle larger volumes of device data and threat detection tasks. The **Celery workers** can be scaled up or down depending on network traffic, ensuring that the system remains responsive even under heavy load.

---

## **Acknowledgements**

- **Chirpstack** for IoT network management.
- **InfluxDB** for time-series data storage.
- **Celery** for background task scheduling and asynchronus task execution.
- **Docker** and **Docker Compose** for containerized deployment and scalability.
- **RabbitMQ** for message queuing and worker communication.
- **Plotly** for building the charts in the frontend dashboard.

---
