import asyncio
import json
import struct
import sys
import time as tim
from concurrent.futures import ThreadPoolExecutor

import discord
import pvporcupine
import pyaudio
import pyttsx3
import requests
import simpleaudio as sa
import speech_recognition as sr
from openai import OpenAI

from utils import Action, get_formatted_actions

with open("config.json", "r") as file:
    config = json.load(file)

USER_OPERATING_SYSTEM = 'windows' if 'win' in sys.platform else ('mac' if 'darwin' in sys.platform else 'linux')

wave_obj = sa.WaveObject.from_wave_file("./acknowledge.wav")
client = discord.Client(intents=discord.Intents.all())
executor = ThreadPoolExecutor()
engine = pyttsx3.init()
# set to female voice
engine.setProperty('rate', 400)
openAICLIENT = OpenAI(api_key=config["OPENAI_KEY"])

weatherapi_url = "https://api.weatherapi.com/v1/current.json"


@Action.register
async def weather(location, date=None, time=None):
    """
    Returns weather based on params
    date: YYYY-MM-DD
    time: Must be in 24 hour. For example 5pm should be time=17, 6 am as time=6
    """
    if not date:
        date = tim.strftime("%Y-%m-%d")

    if not time:
        response = requests.get(f"{weatherapi_url}?key={config['WEATHERAPI_KEY']}&q={location}&dt={date}")
        data = response.json()
        return str(data)
    else:
        response = requests.get(f"{weatherapi_url}?key={config['WEATHERAPI_KEY']}&q={location}&dt={date}&hour={time}")
        data = response.json()
        return str(data)


def get_system_message():
    with open("system_message.txt", "r") as file:
        message = file.read()

    # replace [DYNAMIC DATE] with current date in Sat Jun 12 5:00 PM format
    message = message.replace("[DYNAMIC DATE]", tim.strftime("%a %b %d %I:%M %p"))
    # add actions to the end of the message
    message += get_formatted_actions()

    return message


def get_openai_response(message_thread):
    # Call the chat completions API with the message list
    response = openAICLIENT.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=message_thread
    )

    # Append the response from OpenAI to the message thread
    message_thread.append({"role": "assistant", "content": response.choices[0].message.content})
    return message_thread


def parse_action_response(response):
    if response.startswith("[") and "]" in response:
        action_name = response[1:response.index("]")]
        params_str = response[response.index("(") + 1:response.index(")")]
        params = dict(param.split(": ") for param in params_str.split(", "))
        return action_name, params
    return None, None


async def execute_action(action_name, params):
    if action_name in Action.actions:
        action_func = globals().get(action_name.lower())
        if action_func:
            return await action_func(**params)
    return "Action not found"


async def get_jarvis_response(message):
    # Check if the message is a command, if a key from Action.actions is in the message
    message_thread = [
        {"role": "system", "content": get_system_message()},
        {"role": "user", "content": message},
    ]

    message_thread = get_openai_response(message_thread)

    # check if any element from Action.actions.keys() list is in message_thread[2]["content"]

    if any(action in message_thread[2]["content"] for action in Action.actions.keys()):
        action_name, params = parse_action_response(message_thread[2]["content"])

        result = "Action not found"
        if action_name and params:
            result = await execute_action(action_name, params)

        message_thread.append({"role": "system", "content": "[Action Response] " + result})

        message_thread = get_openai_response(message_thread)

        return message_thread[4]["content"]
    else:
        # No action required, return the response as is
        return message_thread[2]["content"]


def start_audio_stream():
    p = pyaudio.PyAudio()
    porcupine = pvporcupine.create(keywords=["jarvis"], access_key=config["PICOVOICE_ACCESS_KEY"])
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=porcupine.sample_rate, input=True,
                    frames_per_buffer=porcupine.frame_length)
    return stream, p, porcupine


def listen(stream, porcupine, recognizer):
    print('\n\nListening for "Jarvis"...')
    while True:
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        result = porcupine.process(pcm)
        if result >= 0:
            wave_obj.play()
            print("Wake word detected! Start speaking now...")
            with sr.Microphone() as source:
                try:
                    audio_data = recognizer.listen(source, timeout=4, phrase_time_limit=5)
                except sr.WaitTimeoutError:
                    print("Listening timed out.")
                    print('\n\nListening for "Jarvis"...')
                    continue
                try:
                    recognized_text = recognizer.recognize_google(audio_data)
                    return recognized_text
                except (sr.UnknownValueError, sr.RequestError) as e:
                    print(f"Speech recognition error: {e}")


async def handle_commands():
    stream, p, porcupine = start_audio_stream()
    recognizer = sr.Recognizer()
    try:
        while True:
            recognized_text = await asyncio.get_running_loop().run_in_executor(executor, listen, stream, porcupine,
                                                                               recognizer)
            if recognized_text:
                try:
                    await process_commands(recognized_text)
                except Exception as e:
                    print(f"An error occurred while processing the command: {e}")
                    engine.say("Sorry sir, an error occurred while processing your command.")
                    engine.runAndWait()
    finally:
        stream.stop_stream()
        stream.close()
        porcupine.delete()
        p.terminate()


async def process_commands(recognized_text):
    response = await get_jarvis_response(recognized_text)
    engine.say(response)
    engine.runAndWait()


@client.event
async def on_ready():
    print('Successfully connected to the discord websocket.')
    await handle_commands()


client.run(config["DISCORD_TOKEN"])
