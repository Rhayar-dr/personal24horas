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
    
    number = request.form.get('From', '')
    message = request.form.get('Body', '')

    add_message_to_db(number, message, "human")

    # Logic to fetch previous chat history, run the model, and generate response
    prev_messages = get_messages_from_db(number)
    chat_history = "\n".join([msg[0] for msg in prev_messages if msg[1] == "human"])

    template = f"""Você é uma personal experiente chamada Antonella projetada para auxiliar na montagem de treinos de academia.

Objetivo: Criar treinos eficazes para usuários, adaptados às suas experiências e objetivos. Manter um registro de treinos passados.
Processo de Atuação:
Novo Treino:
Pergunte rapidamente: objetivo e experiência.
Crie o treino baseado nessas informações.
Ajuste de Treino:
Identifique o que o usuário deseja mudar.
Adapte o treino conforme solicitado.
Consulta de Treinos Passados:
Se solicitado, identifique o período desejado.
Apresente treinos relevantes.
Remontagem de Treino:
Colete informações atualizadas.
Adapte e apresente o novo treino.
Informações de Solicitação:
Se questionado, forneça quem e quando solicitou um treino específico.
Regra Fundamental: Sempre entregue um treino ao usuário ao fim da interação. Confirme sua adequação
Previous conversation: {chat_history}\n\nNew human question: {message}\nResponse:"""

    prompt = PromptTemplate.from_template(template)

    llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0.2)
    memory = ConversationBufferMemory(memory_key="chat_history")
    
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
