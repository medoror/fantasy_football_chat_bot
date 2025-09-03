FROM python:3.9.9-slim-bullseye

# Install app
ADD . /usr/src/gamedaybot
WORKDIR /usr/src/gamedaybot

# Install requirements first to handle dependency conflicts
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 setup.py install

# Launch app
CMD ["python3", "gamedaybot/espn/espn_bot.py"]