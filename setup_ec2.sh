#!/bin/bash
# Automated EC2 setup for Streamlit + Bright Data API Docker app (no Selenium/Chrome required)
set -e

# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Optional: Add current user to docker group (avoids sudo)
sudo usermod -aG docker $USER

# Clone or copy your project (if not already present)
# Example: git clone <your-repo-url> linkedinemailagent
# cd linkedinemailagent

# Build Docker image
sudo docker build -t linkedinemailagent .

# Run Docker container
sudo docker run -d -p 8501:8501 --name linkedinemailagent linkedinemailagent

echo "Deployment complete! Access your app at http://<EC2_PUBLIC_IP>:8501"
