# Use an official Python runtime as a parent image
FROM python:3.10-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# Copy the rest of the application code
COPY . .

# Expose ports for backend (8000) and frontend (8501)
EXPOSE 8000
EXPOSE 8501

# The command will be overridden by docker-compose, 
# but we can set a default just in case.
CMD ["python", "run.py"]
