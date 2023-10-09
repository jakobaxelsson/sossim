# Use an official Python runtime as a base image
FROM python:latest

# Set the working directory in the container
WORKDIR /app

# Copy the local project directory into the container at /app
COPY . /app

# Install the project dependencies
RUN pip install -r requirements.txt

# Expose the port that your web server will listen on
EXPOSE 8000

# Define the command to run your application
CMD ["python", "dev_server.py"]