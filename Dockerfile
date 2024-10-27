FROM python:3.10-alpine

# Set the working directory
WORKDIR /app

# Copy the API wrapper code
COPY ./hackathon_bot/ ./hackathon_bot/

# Install API wrapper dependencies
RUN pip install -r hackathon_bot/requirements.txt

# Copy the bot requirements
COPY ./requirements.txt ./

# Install the bot dependencies
RUN pip install -r requirements.txt

# Copy the bot code
COPY . .

# Run the bot
ENTRYPOINT [ "python", "-u", "main.py" ]