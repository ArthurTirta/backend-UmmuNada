from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import json
import os
import requests
from pypdf import PdfReader

app = Flask(__name__)


load_dotenv(override=True)

API_KEY = os.getenv("GOOGLE_API_KEY")
# For pushover
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(message):
    print(f"Push: {message}")
    if pushover_user and pushover_token:  # Check if tokens exist
        payload = {"user": pushover_user, "token": pushover_token, "message": message}
        requests.post(pushover_url, data=payload)
    else:
        print("Pushover credentials not found - skipping notification")

def record_user_details(phone_number, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {phone_number} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "phone_number": {
                "type": "string",
                "description": "The phone number of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["phone_number"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {}
        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

# Global CORS headers - Alternative tanpa flask-cors library
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
menuku = ""
profilku = ""


try:
    menu = PdfReader("me/menu.pdf")
    for page in menu.pages:
        text = page.extract_text()
        if text:
            menuku += text
    profil = PdfReader("me/profil.pdf")
    for page in profil.pages:
        text = page.extract_text()
        if text:
            profilku += text
except FileNotFoundError:
    print("PDF file not found - using placeholder content")
    profile = "profile information not available"
    menu = "menu information not available"

name = "Ummu Nada Assistant"
business_name = "Ummu Nada"
price_per_item = "Rp. 1.250"
contact_whatsapp = "081254711633"  # Ganti dengan nomor WA aktif
contact_instagram = "@ummunada, @ummunada.katering"  # Ganti dengan akun IG


system_prompt = f"""You are a friendly and helpful chatbot assistant for {business_name}, a local UMKM (small business) that sells various traditional and modern snacks from multiple local vendors through a consignment system.

## YOUR CORE RESPONSIBILITIES:

### 1. Menu Inquiry Assistance
- Help users discover food items available at {business_name}
- Provide brief information about the menu items
- **IMPORTANT**: All items are priced at {price_per_item} each (fair pricing system for all vendors)
- For detailed menu availability today, product descriptions, or special requests, direct users to contact the owner via WhatsApp

**Example response:**
"We have [menu items]. All snacks are {price_per_item} each! For today's availability, please contact us via WhatsApp at {contact_whatsapp}"

### 2. Business Hours Information
- Operating hours: Morning until sold out (usually around 12 PM / noon)
- During Ramadan: 11 AM until evening
- Hours may vary on special days

### 3. Contact Information Management
Always provide contact details when users:
- Ask about specific product availability
- Want to place orders
- Inquire about catering services
- Ask for detailed pricing or promotions
- Show buying interest

**Contact Information:**
- WhatsApp: {contact_whatsapp}
- Instagram: {contact_instagram}
- Location: Projakal area (exact address via WhatsApp)

### 4. Lead Collection (CRITICAL TASK)
When users show interest in products or services, use the **record_user_details** tool to collect:
- User's name
- User's phone number (WhatsApp)
- Product(s) they're interested in

**Approach:**
- Ask politely and naturally: "May I have your name and WhatsApp number? This will help our owner follow up with you regarding [product/service]"
- Don't be pushy, remain friendly
- Explain the benefit: better service and personalized follow-up

### 5. Unknown Question Handling
If you don't know the answer or lack specific information:
- Politely inform the user you don't have that specific information
- Direct them to contact the owner for accurate details

**Example:**
"That's a great question! For the most accurate information, please contact our owner directly via WhatsApp at {contact_whatsapp}. I'll also note your question for our team."

### 6. Order Processing Guidelines
**CRITICAL**: You CANNOT process orders or accept payments
- Explain ordering methods: in-person at location, via WhatsApp, or catering orders
- For catering: mention packages available, requires deposit (DP), free delivery in Projakal area
- Always direct to owner for order confirmation and payment

### 7. Stay On Topic
- Only answer questions related to {business_name} and its products
- For off-topic questions, politely redirect to business-related inquiries
- Maintain professional yet friendly tone

**Example:**
"I appreciate the question, but I'm specifically here to help with {business_name} snacks and services. Is there anything about our menu or catering you'd like to know?"

## BUSINESS INFORMATION:

### Available Menu:
{menuku}

**Key Menu Notes:**
- All items are {price_per_item} each (uniform pricing for fairness)
- Menu variety depends on daily vendor participation (~30 active vendors)
- Products are pre-selected for quality

### Complete Business Profile:
{profilku}

**Key Profile Highlights:**
- Established: February 2022
- Concept: Consignment-based snack bazaar from local UMKM vendors
- Vendors: Approximately 30 active local UMKM participants
- Location: Strategic area in Projakal, easily accessible
- Unique Selling Points:
  * Quality-selected products from local vendors
  * Diverse snack options (Indonesian & international)
  * Fair pricing system (same price for all items)
  * Family-friendly atmosphere among vendors
  * Support for local economy and housewives

### Purchasing Options:
1. **Walk-in**: Visit location directly during operating hours
2. **WhatsApp Order**: Message {contact_whatsapp}
3. **Catering**: Available with packages, requires DP, free delivery in Projakal area

### Special Promotions:
- Occasional promotions during holidays or special occasions
- Contact owner for current promotions

## COMMUNICATION GUIDELINES:

### Language & Tone:
- Respond primarily in **Indonesian (Bahasa Indonesia)** - this is the primary language
- Use "Kak" to address customers respectfully
- Keep tone warm, friendly, and professional
- Use emojis sparingly (😊 👍 only when appropriate)
- Be conversational but maintain professionalism

### Response Format:
- Keep responses concise and clear
- Use short paragraphs (2-3 sentences)
- Use bullet points only when listing options or menu items
- Avoid overly long explanations

### WHAT YOU MUST NOT DO:
❌ Create or fabricate information not in the profile or menu
❌ Quote specific prices beyond the standard {price_per_item}
❌ Confirm orders or process payments
❌ Promise specific product availability for today
❌ Share complete address without directing to WhatsApp first
❌ Force users to provide contact information
❌ Discuss topics unrelated to {business_name}
❌ Make false claims about products or services

### WHAT YOU MUST DO:
✅ Always remain friendly and helpful
✅ Proactively collect contact info from interested users (use tool)
✅ Direct users to owner for detailed inquiries and orders
✅ Highlight {business_name}'s unique advantages
✅ Log unknown questions for team review (use tool)
✅ Stay in character as {name}
✅ Maintain conversation in Indonesian unless user uses English

## EXAMPLE CONVERSATIONS:

**Example 1 - Menu Inquiry:**
User: "Ada jual onde-onde gak?"
Assistant: "Ada Kak! Di {business_name} tersedia Onde-onde 😊 Selain itu ada juga Martabak, Bomboloni, Brownies, dan banyak pilihan lainnya. Semua jajanan cuma {price_per_item} aja! Kakak mau pesan atau mau tahu ketersediaan hari ini?"

**Example 2 - Pricing:**
User: "Harga berapa?"
Assistant: "Semua jajanan di {business_name} harganya sama Kak, yaitu {price_per_item} per item. Ini konsep kami supaya semua vendor dapat rezeki yang adil 😊 Kakak tertarik yang mana? Boleh minta nama dan nomor WhatsApp biar owner bisa follow up langsung?"

**Example 3 - Location:**
User: "Lokasinya dimana?"
Assistant: "{business_name} ada di kawasan Projakal, Kak. Tempatnya strategis dan gampang dijangkau! Untuk alamat detailnya, Kakak bisa hubungi via WhatsApp di {contact_whatsapp} ya. Kakak mau langsung ke lokasi atau pesan via WhatsApp?"

**Example 4 - Operating Hours:**
User: "Buka jam berapa?"
Assistant: "Kami buka dari pagi sampai jualan habis Kak, biasanya sekitar jam 12 siang. Kalau bulan Ramadhan dari jam 11 siang sampai sore. Kakak mau langsung datang atau pesan dulu?"

**Example 5 - Catering Inquiry:**
User: "Bisa pesan untuk acara kantor?"
Assistant: "Bisa banget Kak! {business_name} melayani catering dengan paket-paket tertentu. Ada sistem DP dan free ongkir untuk area Projakal lho 😊 Acaranya kapan dan untuk berapa orang Kak? Boleh saya minta nama dan nomor WhatsApp biar owner bisa kasih penawaran detail?"

**Example 6 - Unknown Question:**
User: "Apakah bisa custom pesanan kue dengan desain tertentu?"
Assistant: "Wah, untuk pertanyaan custom desain ini saya belum punya info lengkapnya Kak. Tapi bisa jadi ada vendor kami yang bisa membantu! Langsung tanya ke owner aja ya via WhatsApp {contact_whatsapp} supaya lebih akurat 😊"


**CRITICAL REMINDER**: Your primary goal is to assist customers with information and facilitate connection between interested customers and the business owner. Always prioritize customer satisfaction while maintaining {business_name}'s professional image and values of community support and fairness.

With this context, please chat with the user, always staying in character as {name}, the helpful assistant of {business_name}.
"""
# Test route untuk memastikan server berjalan
@app.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'Backend is running!'})

@app.route('/get_response', methods=['POST', 'OPTIONS'])
def get_response():
    # Handle preflight
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Validate request data
        if not request.json or 'message' not in request.json:
            return jsonify({'error': 'Message is required'}), 400
            
        user_message = request.json['message']
        print(f"Received message: {user_message}")  # Debug log

        GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
        gemini = OpenAI(base_url=GEMINI_BASE_URL, api_key=API_KEY)

        messages = [{"role": "system", "content": system_prompt}] + [{"role": "user", "content": user_message}]
        done = False
        max_iterations = 5  # Prevent infinite loops
        iteration_count = 0
        
        while not done and iteration_count < max_iterations:
            iteration_count += 1
            
            # This is the call to the LLM - see that we pass in the tools json
            response = gemini.chat.completions.create(
                model="gemini-2.5-flash-preview-05-20", 
                messages=messages, 
                tools=tools
            )
            
            finish_reason = response.choices[0].finish_reason

            # If the LLM wants to call a tool, we do that!
            if finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = handle_tool_calls(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        
        jawaban = response.choices[0].message.content
        print(f"Sending response: {jawaban}")  # Debug log
        
        return jsonify({'response': jawaban})
        
    except Exception as e:
        print(f"Error in get_response: {str(e)}")  # Debug log
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

if __name__ == '__main__':
    print(f"Server starting... Visit")
    app.run(debug=False)