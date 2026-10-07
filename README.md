# AI Voice Waiter & Restaurant Management System

> **An AI-powered voice waiter that lets restaurant customers place orders naturally over a phone call while restaurant staff manage tables, orders, transcripts, and billing from a real-time dashboard.**

Veena Stores combines **voice AI, real-time communication, speech recognition, LLMs, text-to-speech, and restaurant management** into a single system.

Instead of waiting for a waiter to take an order, a customer can interact with an AI waiter over a phone call.

The system understands the customer's speech, processes the conversation using an LLM, responds using AI-generated speech, extracts the final order, and updates the restaurant dashboard automatically.

---

## 🎥 What Does It Do?

A customer selects their table and calls the AI waiter.

The system then:

```text
Customer
   ↓
Phone Call
   ↓
Twilio
   ↓
WebSocket Media Stream
   ↓
Deepgram Speech-to-Text
   ↓
Groq LLM
   ↓
AI Response
   ↓
Voicebox TTS
   ↓
Twilio
   ↓
Customer
```

After the conversation ends:

```text
Conversation
     ↓
LLM Order Extraction
     ↓
Menu Matching
     ↓
SQLite Database
     ↓
Restaurant Dashboard
     ↓
Order + Transcript + Bill
```

---

# ✨ Key Features

### 🎙️ AI Voice Waiter

Customers can speak naturally with an AI waiter instead of interacting with a traditional chatbot.

The AI waiter can:

- Understand customer speech
- Answer menu-related questions
- Take food orders
- Understand quantities
- Handle basic customizations
- Ask whether the customer wants anything else
- Confirm the order
- End the call automatically

---

### 📞 Real-Time Phone Calls

The system uses **Twilio** to connect the customer with the AI waiter.

The voice stream is handled through a WebSocket connection, allowing audio to flow between the customer and the AI system in real time.

---

### 🗣️ Speech-to-Text

Customer speech is converted into text using **Deepgram**.

The system uses:

- `nova-2`
- `en-IN`
- 8 kHz μ-law audio
- Real-time transcription
- Endpointing for detecting the end of an utterance

---

### 🧠 LLM-Powered Conversation

**Groq + Llama 3.3 70B** powers the conversation.

The LLM is responsible for:

- Understanding customer requests
- Maintaining conversation context
- Answering menu questions
- Handling unavailable items
- Understanding customizations
- Deciding when the customer has finished ordering

The AI waiter follows a restaurant-specific system prompt and only offers items from the official menu.

---

### 🔊 AI Text-to-Speech

The AI response is converted into speech using **Voicebox / LuxTTS**.

The generated audio is converted into:

```text
WAV
 ↓
8 kHz
 ↓
Mono
 ↓
μ-law
 ↓
Base64
 ↓
Twilio Media Stream
```

This allows the AI response to be played back through the phone call.

---

### 🍛 Automatic Order Extraction

Once the conversation ends, the system sends the conversation transcript to the LLM again.

The LLM extracts structured orders such as:

```json
[
  {
    "item": "Masala Dosa",
    "qty": 2
  },
  {
    "item": "Filter Coffee",
    "qty": 1
  }
]
```

The extracted item is then matched against the official restaurant menu before being stored.

---

### 🧾 Restaurant Dashboard

Restaurant staff can view:

- Available tables
- Occupied tables
- Customer transcript
- Ordered items
- Quantities
- Prices
- Subtotal
- GST
- Final bill

---

### 🧑‍💼 Manager Dashboard

The dashboard provides a visual floor map of the restaurant.

```text
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Table 1 │  │ Table 2 │  │ Table 3 │
│Available│  │Occupied │  │Available│
└─────────┘  └─────────┘  └─────────┘
```

Occupied tables can be opened to view the conversation and order.

---

### 📄 PDF Billing

The manager can generate a PDF bill containing:

- Restaurant name
- Table number
- Date
- Ordered items
- Quantity
- Price
- Subtotal
- GST
- Final total

---

### 📝 Google Forms Integration

The project also supports a Google Forms → Apps Script → FastAPI workflow.

```text
Google Form
     ↓
Apps Script
     ↓
FastAPI /form-submit
     ↓
Extract Table Number
     ↓
Twilio Call
```

The webhook accepts arbitrary form fields and searches for a field containing `"table"` to determine the table number.

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │      Customer       │
                         │    Phone / Device   │
                         └──────────┬──────────┘
                                    │
                                    │ Phone Call
                                    ▼
                         ┌─────────────────────┐
                         │       Twilio        │
                         └──────────┬──────────┘
                                    │
                                    │ WebSocket
                                    ▼
                    ┌──────────────────────────────┐
                    │       FastAPI Backend        │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │   WebSocket Gateway     │  │
                    │  └───────────┬────────────┘  │
                    └──────────────┼───────────────┘
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                │
                  ▼                ▼                ▼
           ┌───────────┐    ┌───────────┐    ┌───────────┐
           │ Deepgram  │    │   Groq    │    │ Voicebox  │
           │   STT     │    │   LLM     │    │    TTS    │
           └───────────┘    └───────────┘    └───────────┘
                  │                │                │
                  └────────────────┼────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │     SQLite      │
                          │                 │
                          │ Tables          │
                          │ Orders          │
                          │ Transcripts     │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ React Dashboard │
                          │                 │
                          │ Floor Map       │
                          │ Orders          │
                          │ Transcript      │
                          │ Billing         │
                          └─────────────────┘
```

---

# 🔄 Voice Conversation Flow

The complete voice interaction works like this:

### 1. Customer selects a table

The customer chooses a table from the Customer Simulator.

### 2. Backend initiates the call

FastAPI receives:

```json
{
  "table_number": 5
}
```

The backend requests Twilio to call the configured customer number.

### 3. Twilio connects to the backend

Twilio requests the TwiML endpoint:

```text
/call-twiml/{table_number}
```

The backend responds with a WebSocket media stream.

### 4. Customer speaks

Customer:

> "I want two masala dosas and one filter coffee."

### 5. Deepgram transcribes the speech

```text
"I want two masala dosas and one filter coffee"
```

### 6. Groq processes the request

The conversation history and restaurant system prompt are sent to the LLM.

### 7. AI responds

Example:

> "Sure, two masala dosas and one filter coffee. Any customizations needed for these?"

### 8. Voicebox generates audio

The response is converted into speech.

### 9. Twilio plays the response

The audio is streamed back to the customer's phone.

### 10. Customer finishes

The AI asks:

> "Is there anything more?"

Customer:

> "No, that's all."

The AI ends with:

> "Perfect, I've sent that to the kitchen. Enjoy your meal!"

### 11. Order extraction

The complete conversation is analyzed and converted into structured order data.

### 12. Dashboard update

The restaurant manager can view the order and transcript.

---

# 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| HTTP Client | Axios |
| Backend | FastAPI |
| Database | SQLite |
| Voice Telephony | Twilio |
| Speech-to-Text | Deepgram |
| LLM | Groq / Llama 3.3 70B |
| Text-to-Speech | Voicebox / LuxTTS |
| Real-Time Communication | WebSockets |
| PDF Generation | jsPDF |
| Tunnel | ngrok |
| Google Integration | Google Apps Script |

---

# 📁 Project Structure

```text
Veena-Stores/
│
├── main.py
├── database.py
├── menu.py
├── requirements.txt
├── .env.example
├── .gitignore
├── apps_script.js
│
├── restaurant.db
│
└── frontend/
    │
    ├── package.json
    ├── index.html
    │
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── App.css
        └── index.css
```

### Backend

`main.py`

Contains:

- FastAPI application
- REST APIs
- Twilio integration
- WebSocket media streaming
- Deepgram integration
- Groq integration
- Voicebox integration
- Order extraction

### Database

`database.py`

Handles:

- Restaurant tables
- Orders
- Transcripts
- Table availability

### Menu

`menu.py`

Contains the official restaurant menu and prices.

This acts as the single source of truth for menu validation.

---

# 🚀 Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/veena-stores.git

cd veena-stores
```

---

# 🐍 Backend Setup

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a `.env` file in the backend root:

```env
TWILIO_SID=your_twilio_sid
TWILIO_TOKEN=your_twilio_auth_token
TWILIO_NUMBER=your_twilio_phone_number

GROQ_KEY=your_groq_api_key

DEEPGRAM_KEY=your_deepgram_api_key

SERVER_URL=https://your-ngrok-url.ngrok-free.app
```

### Required Services

You will need API credentials for:

- Twilio
- Groq
- Deepgram

You will also need a running local Voicebox instance for TTS.

---

# 🔊 Voicebox Setup

Veena Stores currently communicates with a local Voicebox API.

The backend expects Voicebox at:

```text
http://127.0.0.1:17493
```

The TTS endpoint used by the backend is:

```text
/generate
```

The generated audio is then converted into Twilio-compatible μ-law audio.

Make sure Voicebox is running before testing voice calls.

---

# 🌐 Start ngrok

Twilio needs a publicly accessible URL to reach your local FastAPI server.

Start FastAPI first:

```bash
uvicorn main:app --reload --port 8000
```

Then expose it:

```bash
ngrok http 8000
```

Copy the HTTPS URL:

```text
https://example.ngrok-free.app
```

and update:

```env
SERVER_URL=https://example.ngrok-free.app
```

Restart FastAPI after changing the environment variable.

---

# ⚛️ Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

The frontend will be available at the Vite development URL.

---

# ▶️ Running the Complete System

You need these components running:

```text
Terminal 1
──────────
FastAPI
uvicorn main:app --reload --port 8000


Terminal 2
──────────
Frontend
npm run dev


Terminal 3
──────────
ngrok
ngrok http 8000


Voicebox
────────
Local TTS service
127.0.0.1:17493
```

---

# 🔌 API Endpoints

## Start a Call

```http
POST /call
```

Request:

```json
{
  "table_number": 5
}
```

---

## Google Forms Webhook

```http
POST /form-submit
```

Example:

```json
{
  "Table Number": "5",
  "Name": "Customer"
}
```

The backend searches for a field containing `"table"` and extracts the table number.

---

## Get All Tables

```http
GET /api/tables
```

---

## Get Table Details

```http
GET /api/tables/{table_id}
```

Returns:

- Orders
- Latest transcript

---

## Checkout

```http
POST /api/tables/{table_id}/checkout
```

This clears the table's current order/transcript and marks the table as available.

---

## TwiML

```http
GET /call-twiml/{table_number}
```

Provides Twilio with the WebSocket streaming configuration.

---

## WebSocket

```text
/media-stream/{table_number}
```

Handles real-time Twilio audio streaming.

---

# 🗄️ Database

Veena Stores currently uses SQLite.

### Tables

#### `tables`

```text
id
status
```

#### `orders`

```text
id
table_id
item_name
quantity
price
```

#### `transcripts`

```text
id
table_id
text
```

The database is initialized with 20 restaurant tables.

---

# 🧠 AI Architecture

The project uses multiple specialized AI components instead of relying on one model for everything.

```text
                 ┌───────────────┐
Customer Speech ─►│   Deepgram    │
                 │      STT       │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │      Groq     │
                 │ Llama 3.3 70B │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │    Voicebox   │
                 │     TTS       │
                 └───────┬───────┘
                         │
                         ▼
                    Customer
```

The same LLM is also used after the call to extract structured order information from the conversation.

---

# 🛡️ Design Decisions

### Why WebSockets?

Traditional HTTP request/response communication is not ideal for continuous voice streaming.

WebSockets allow the backend to maintain a real-time audio connection between Twilio and the AI pipeline.

---

### Why a Queue for Transcriptions?

Speech can arrive while the LLM is processing the previous request.

The project uses an asynchronous queue so transcription results are not immediately discarded.

```text
Deepgram
   ↓
asyncio.Queue
   ↓
Conversation Processor
   ↓
Groq
```

---

### Why Separate STT, LLM and TTS?

Each component has a specialized responsibility:

```text
STT → Understand speech
LLM → Understand intent + generate response
TTS → Speak response
```

This makes the system modular and allows individual components to be replaced later.

---

# 🎯 Demo Scenario

A typical demonstration:

```text
1. Open Customer Simulator

2. Select Table 5

3. Click "Call Waiter"

4. Phone rings

5. Customer speaks:

   "I want two masala dosas and one filter coffee."

6. AI responds:

   "Sure, two masala dosas and one filter coffee.
    Any customizations needed for these?"

7. Customer:

   "No."

8. AI:

   "Is there anything more?"

9. Customer:

   "No, that's all."

10. AI:

    "Perfect, I've sent that to the kitchen.
     Enjoy your meal!"

11. Call ends

12. Manager Dashboard updates

13. Manager opens Table 5

14. Transcript + order appear

15. Manager generates the bill

16. Manager checks out the table
```

---

# 📊 Current Capabilities

- [x] AI voice waiter
- [x] Phone-based interaction
- [x] Real-time speech recognition
- [x] LLM conversation
- [x] AI-generated voice
- [x] Menu-aware conversations
- [x] Order extraction
- [x] Fuzzy menu matching
- [x] Restaurant table management
- [x] Call transcripts
- [x] Order dashboard
- [x] PDF billing
- [x] Google Forms webhook
- [x] Table checkout
- [x] Real-time WebSocket communication

---

# 🚧 Current Limitations

This project is currently designed as a **hackathon/demo prototype**.

Some components are intentionally simplified.

### Current limitations include:

- SQLite is used instead of a production database.
- Customer phone number is currently configured for the Twilio trial/demo flow.
- Voicebox runs locally.
- ngrok is required for exposing the local backend to Twilio.
- Authentication is not implemented.
- Dashboard API authorization is not implemented.
- Historical order management is limited.
- TTS depends on a locally running Voicebox service.
- The current system is optimized for a single restaurant deployment.

---

# 🔮 Future Improvements

### Multi-Restaurant SaaS

Support multiple restaurants from one platform.

```text
Restaurant A
Restaurant B
Restaurant C
      ↓
Shared Platform
```

---

### Production Database

Move from SQLite to:

- PostgreSQL
- Redis for real-time state
- Object storage for recordings/transcripts

---

### Kitchen Display System

Automatically send confirmed orders to a kitchen display.

```text
Customer
   ↓
AI Waiter
   ↓
Order
   ↓
Kitchen Display
   ↓
Chef
```

---

### Multi-Language Voice Support

Support:

- English
- Kannada
- Hindi
- Telugu
- Tamil
- Other regional languages

---

### Human Handoff

If the AI cannot understand the customer after several attempts:

```text
AI Waiter
    ↓
Unable to resolve
    ↓
Human Waiter
```

---

### Payment Integration

Future versions could integrate:

- UPI
- Razorpay
- Stripe

allowing customers to complete payment directly after ordering.

---

### Advanced Restaurant Analytics

Future dashboards could provide:

- Most ordered dishes
- Peak ordering times
- Average order value
- Table turnover
- AI call success rate
- Customer wait time
- Order correction rate

---

# 🔒 Security

Never commit secrets to GitHub.

The project uses environment variables for:

```text
TWILIO_SID
TWILIO_TOKEN
GROQ_KEY
DEEPGRAM_KEY
```

The `.gitignore` also excludes `.env` and generated database/audio files.

Before deploying publicly, additional security should be implemented:

- API authentication
- Rate limiting
- Webhook signature verification
- Input validation
- Database access controls
- Secret management
- HTTPS
- Proper CORS configuration

---

# 🤝 Contributing

Contributions are welcome.

```bash
# Fork the repository

# Create a branch
git checkout -b feature/your-feature

# Make your changes

# Commit
git commit -m "Add your feature"

# Push
git push origin feature/your-feature
```

Then open a Pull Request.

---

# 📜 License

This project is currently provided for educational, experimental, and hackathon purposes.

Add your preferred license here, such as MIT, if you intend to release it as open source.

---

# 👨‍💻 Author

**Charan**

Built as an exploration of:

- Voice AI
- Real-time communication
- LLM-powered agents
- Speech technologies
- Restaurant automation
- Full-stack development

---

# ⭐ If You Like This Project

If you found Veena Stores interesting, consider giving the repository a ⭐ on GitHub.

---

## 💡 The Vision

Veena Stores is more than a restaurant chatbot.

The long-term vision is to build an **AI-powered restaurant operating system** where voice agents can handle customer interactions while restaurant staff focus on delivering the actual dining experience.

```text
             AI RESTAURANT
                  │
       ┌──────────┼──────────┐
       │          │          │
     Voice      Orders     Tables
       │          │          │
       └──────────┼──────────┘
                  │
              Analytics
                  │
                  ▼
          Smarter Restaurant
```

**Built with ❤️ using FastAPI, React, Twilio, Deepgram, Groq and Voicebox.**