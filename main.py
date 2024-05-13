import discord
import asyncio
import pyaudio
import numpy as np
import whisper

TOKEN = 'NTM4MTQzNjE5NDU5MDU1NjM3.GKmaMi.1QlWpuUPUIXq4WUTCK4hqC4D577pc8vvXCXzkE'  # Replace with your bot's token
CHANNEL_ID = 793214658194178088  # Replace with your channel ID
GUILD_ID = 793213521181147178

client = discord.Client()
model = whisper.load_model("small")


def start_audio_stream():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    return stream, p


async def continuously_listen(stream):
    print("Listening for 'Hey Jarvis'...")
    while True:
        data = stream.read(1024, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0  # Normalize audio
        audio = whisper.pad_or_trim(audio)  # Adjust length if necessary

        # Process audio chunk
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        result = whisper.decode(model, mel, whisper.DecodingOptions(), task="transcribe")

        if "hey jarvis" in result.text.lower():

            return result.text  # Detected the activation phrase
        else:
            print(f"Activation command not recognized: {result.text}")


async def handle_commands():
    stream, p = start_audio_stream()
    try:
        while True:
            recognized_text = await continuously_listen(stream)
            print(f"Activation command recognized: {recognized_text}")

            # Check for specific commands
            command = recognized_text.lower().replace("hey jarvis", "").strip()
            if command.startswith("send") and command.endswith("in the groupchat"):
                message = command[5:-15].strip()
                channel = client.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(message)
                else:
                    print("Channel not found!")
            elif command.startswith("tell") and command.endswith("in discord"):
                parts = command.split()
                if len(parts) >= 3:
                    nickname = parts[1].lower()
                    message = ' '.join(parts[2:-2])
                    guild = client.get_guild(GUILD_ID)
                    if guild:
                        user = discord.utils.find(
                            lambda m: (m.nick and m.nick.lower() == nickname) or m.name.lower() == nickname,
                            guild.members)
                        if user:
                            channel = client.get_channel(CHANNEL_ID)
                            if channel:
                                await channel.send(f"{user.mention} {message.strip()}")
                            else:
                                print("Channel not found!")
                        else:
                            print(f"User with nickname or username '{nickname}' not found in guild.")
                    else:
                        print("Guild not found!")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    await handle_commands()


client.run(TOKEN)
