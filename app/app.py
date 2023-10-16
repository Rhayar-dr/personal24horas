from flask import Flask, request, jsonify
import sqlite3
from twilio.twiml.messaging_response import MessagingResponse
from langchain import LLMChain
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

DATABASE = 'whatsapp_chat.db'

app = Flask(__name__)

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history
                          (number TEXT, content TEXT, msg_type TEXT)''')

def add_message_to_db(number, content, msg_type):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (number, content, msg_type) VALUES (?, ?, ?)",
                       (number, content, msg_type))

def get_messages_from_db(number):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, msg_type FROM chat_history WHERE number=?", (number,))
        return cursor.fetchall()

@app.route('/bot', methods=['POST'])
def bot_response():
    data = request.get_json()
    number = data.get('From', '')
    message = data.get('Body', '')

    add_message_to_db(number, message, "human")

    # Logic to fetch previous chat history, run the model, and generate response
    prev_messages = get_messages_from_db(number)
    chat_history = "\n".join([msg[0] for msg in prev_messages if msg[1] == "human"])

    template = f"Instrução para a IA de Montagem de Treinos:\n{chat_history}\n\nNew human question: {message}\nResponse:"
    prompt = PromptTemplate.from_template(template)

    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0.2)
    memory = ConversationBufferMemory(memory_key="chat_history")
    readonlymemory = ReadOnlySharedMemory(memory=memory)
    
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True,
        memory=memory
    )

    # Adjusted the input format for llm_chain.run()
    input_data = {
        'chat_history': chat_history,
        'question': message
    }

    response = llm_chain.run(input_data)
    add_message_to_db(number, response, "ai")

    # Send response to user
    resp = MessagingResponse()
    resp.message(response)
    return str(resp)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8000)
