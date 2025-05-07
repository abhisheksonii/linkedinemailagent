FROM python:3.10-slim

USER root

# Install Chrome and system dependencies for Selenium/ChromeDriver
RUN apt-get update && \
    apt-get install -y wget gnupg2 unzip fonts-liberation libnss3 libxss1 libgconf-2-4 libappindicator3-1 libasound2 libatk-bridge2.0-0 libgtk-3-0 libgbm1 && \
    wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y /tmp/chrome.deb && \
    rm /tmp/chrome.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code, including .env and app/
COPY . .

# Expose the port Streamlit will run on
EXPOSE 8501

# Run Streamlit app using main.py
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
