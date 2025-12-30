<body>

  <h1>🤖 Beru – Telegram AI Assistant (Gemini Powered)</h1>

  <p>
    <strong>Beru</strong> is a lightweight <strong>Telegram bot</strong> powered by
    <strong>Google Gemini 2.5 Flash</strong>. It responds intelligently to user messages,
    handles basic commands, and beautifies AI-generated responses before sending them back.
  </p>

  <p>
    This is a <strong>functional MVP</strong>, not a demo script.
  </p>

  <hr>

  <h2>🚀 Features</h2>
  <ul>
    <li>🧠 Powered by Google Gemini 2.5 Flash</li>
    <li>💬 Telegram integration using telepot</li>
    <li>👋 Custom greeting & identity commands</li>
    <li>✨ Auto-beautified AI responses</li>
    <li>🔐 Secure API keys via environment variables</li>
  </ul>

  <hr>

  <h2>🧩 Tech Stack</h2>
  <ul>
    <li>Python 3.9+</li>
    <li>telepot</li>
    <li>google-generativeai</li>
    <li>Environment variables for secrets</li>
  </ul>

  <hr>

  <h2>📁 Project Structure</h2>
  <pre>
.
├── bot.py
├── README.md
└── requirements.txt
  </pre>

  <hr>

  <h2>📦 Installation</h2>

  <h3>1️⃣ Clone the Repository</h3>
  <pre>
git clone https://github.com/your-username/beru-telegram-bot.git
cd beru-telegram-bot
  </pre>

  <h3>2️⃣ Install Dependencies</h3>
  <pre>
pip install -r requirements.txt
  </pre>

  <hr>

  <h2>🔑 Environment Variables</h2>

  <p>Set the following environment variables:</p>

  <pre>
export API_KEY="YOUR_GEMINI_API_KEY"
export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
  </pre>

  <p><strong>Warning:</strong> Never hardcode API keys. That’s amateur hour.</p>

  <hr>

  <h2>▶️ Usage</h2>

  <pre>
python bot.py
  </pre>

  <p>Supported interactions:</p>
  <ul>
    <li><code>hi</code>, <code>hello</code>, <code>hey</code> → Greeting</li>
    <li><code>who are you</code> → Identity response</li>
    <li>Any other text → Processed by Gemini AI</li>
  </ul>

  <hr>

  <h2>🧠 How It Works</h2>
  <ol>
    <li>Telegram receives a message</li>
    <li>telepot parses message metadata</li>
    <li>Predefined commands return static replies</li>
    <li>Other messages are sent to Gemini</li>
    <li>Gemini response is beautified and returned</li>
  </ol>

  <hr>

  <h2>📜 requirements.txt</h2>
  <pre>
telepot
google-generativeai
  </pre>

  <hr>

  <br>
  <h2>Use the Bot Here👇</h2>
  <img width="500" height="1000" alt="image" src="https://github.com/user-attachments/assets/8d2c0023-c350-4dde-91da-e87da1a75f2d" />
  
</body>
</html>
