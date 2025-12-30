import time
import telepot
import google.generativeai as genai
import os

# Configure the API key
genai.configure(api_key=os.getenv("API_KEY"))
bot_token=os.getenv("BOT_TOKEN")

# Initialize the model
model = genai.GenerativeModel("gemini-2.5-flash")

def telebot(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type == "text":
        command = msg["text"]
        print("Got Command: %s" % command)
        if command.lower() in ["hello", "hey", "sup", "hi"]:
            bot.sendMessage(chat_id, "Hey iam Beru,How can i assist you my king?")
        elif command.lower() in ["who are you", "what is your name"] or "name" in command.lower():
            bot.sendMessage(chat_id, "I am Beru, your personal AI assistant powered by Google Gemini-2.5.")
        else:
            # Send the user's message to Gemini and get response
            try:
                response = model.generate_content(command)
                response = model.generate_content("Beautify this text: "+response.text)
                reply = response.text
                bot.sendMessage(chat_id, reply)
            except Exception as e:
                bot.sendMessage(chat_id, "Sorry, I couldn't process your request. Error: " + str(e))


bot = telepot.Bot(bot_token)
bot.message_loop(telebot)

while 1:
    time.sleep(2000)