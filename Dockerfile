# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages
RUN pip install --no-cache-dir fastapi uvicorn pydantic python-dotenv ibm_watsonx_ai requests

COPY app.py /app/app.py


# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set environment variables for Watsonx API key and URL (to be set at runtime)
# use in RHOS
#ENV WATSONX_IAM_APIKEY="put here IAM api key" 
#ENV WATSONX_PROJECT_ID="put here wx.ai project id" 
#ENV WATSONX_API_URL="https://us-south.ml.cloud.ibm.com or put other link" 
#ENV CHROMA_URL="https://where is your chroma service/search" 
#ENV RETRIVER="chroma" 
#ENV CHROMA_FOR_WD_PROJECT="[{'chroma':'https://I think it is unused for now/search','WATSONX_PROJECT_ID':'I think it is unused for now' }]" 
#ENV NUMBER_OF_RESPONSES_FOR_GENAI=2 
#ENV WATSONX_MODEL_ID="ibm/granite-8b-code-instruct" 

# Define environment variable for Python to avoid buffering
ENV PYTHONUNBUFFERED=1

# Run the FastAPI app with Uvicorn when the container launches
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]