# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install the Python dependencies first (this layer is cached between builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app into the container
COPY . .

# Expose the port Streamlit listens on
EXPOSE 8501

# Start the Streamlit app on port 8501
# (CORS and XSRF protection are disabled so that file uploads work behind the Codespaces port-forwarding proxy)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
