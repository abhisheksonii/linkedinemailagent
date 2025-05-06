# Use Selenium's official Chrome image with Python pre-installed

USER root

# Install Python and pip (if not present) and Streamlit dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip

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
