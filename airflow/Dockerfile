# Use the official Airflow image as a parent image
FROM apache/airflow:2.9.3

# The backend code is now mounted via docker-compose.yml, no need to COPY.

# Copy the requirements file for airflow
COPY ./airflow/requirements.txt /opt/airflow/requirements.txt

# Install Python dependencies as root
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt

ENV PYTHONPATH "/opt/airflow/dags:/opt/airflow/backend"

# Switch back to the airflow user
USER airflow
