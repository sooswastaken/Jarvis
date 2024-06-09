import json
from openai import OpenAI
from utils import Action, getFormattedActions
import time as tim
import requests

with open("config.json", "r") as file:
    config = json.load(file)

openAICLIENT = OpenAI(api_key=config["OPENAI_KEY"])

weatherapi_url = "https://api.weatherapi.com/v1/current.json"


@Action.register
def weather(location, date=None, time=None):
    """
    Returns weather based on params
    date: YYYY-MM-DD
    time: 24HR fmt (only hr no minutes) (DO NOT SPECIFY FOR CURRENT WEATHER)
    """
    if not date:
        date = tim.strftime("%Y-%m-%d")

    if not time:
        response = requests.get(f"{weatherapi_url}?key={config['WEATHERAPI_KEY']}&q={location}&dt={date}")
        data = response.json()
        return str(data)
    else:
        "Specific weather is not available at the moment"





def get_system_message():
    with open("system_message.txt", "r") as file:
        message = file.read()

    # replace [DYNAMIC DATE] with current date in Sat Jun 12 5:00 PM format
    message = message.replace("[DYNAMIC DATE]", tim.strftime("%a %b %d %I:%M %p"))
    # add actions to the end of the message
    message += getFormattedActions()

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


def execute_action(action_name, params):
    if action_name in Action.actions:
        action_func = globals().get(action_name.lower())
        if action_func:
            return action_func(**params)
    return "Action not found"


def get_jarvis_response(message):
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
            result = execute_action(action_name, params)

        message_thread.append({"role": "system", "content": "[Action Response] " + result})

        message_thread = get_openai_response(message_thread)

        return message_thread[4]["content"]
    else:
        # No action required, return the response as is
        return message_thread[2]["content"]


def main():
    while True:
        user_input = input("Enter your message for Jarvis: ")
        print(get_jarvis_response(user_input))


if __name__ == "__main__":
    main()
