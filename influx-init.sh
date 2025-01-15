#!/bin/bash
set -e


# Create additional buckets
echo "Creating additional buckets..."
influx bucket create -n "$DEV_BUCKET" -o "$DOCKER_INFLUXDB_INIT_ORG" -t "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" -r 7d -d "Avg Device Metrics"
influx bucket create -n "$GW_BUCKET" -o "$DOCKER_INFLUXDB_INIT_ORG" -t "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" -r 7d -d "Avg Gateway Metrics"

# Validate bucket creation
for bucket in "$DEV_BUCKET" "$GW_BUCKET"; do
  if ! influx bucket find -n "$bucket" -t "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"; then
    echo "Failed to create bucket: $bucket"
    exit 1
  fi
done

# Create tasks

echo "Creating tasks..."
influx task create -o "$DOCKER_INFLUXDB_INIT_ORG" -t "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" -f /flux_tasks/avg_dev_metrics.flux

influx task create -o "$DOCKER_INFLUXDB_INIT_ORG" -t "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" -f /flux_tasks/avg_gw_metrics.flux

# Validate tasks creation
for task in "Dev_Metrics_Task" "Gw_Metrics_Task"; do
  if ! influx task list -t "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" | grep -q "$task"; then
    echo "Failed to create task: $task"
    exit 1
  fi
done

echo "Initialization complete!"

