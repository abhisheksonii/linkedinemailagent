# Use Selenium's official Chrome image with Python pre-installed
FROM selenium/standalone-chrome:latest

USER root

# Install Python and pip (if not present) and Streamlit dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip

# Copy your code into the container
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Expose Streamlit's default port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
