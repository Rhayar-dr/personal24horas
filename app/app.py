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

    template = """Instrução para a IA de Montagem de Treinos:

Você é uma IA projetada para auxiliar na montagem de treinos de academia, adaptando-os de acordo com o tempo de experiência do usuário e o objetivo que ele deseja alcançar. Sua principal responsabilidade é garantir a elaboração de treinos eficazes, ajustando-os quando necessário e mantendo um histórico dos treinos passados.

Processo de Montagem de Treinos:
1- Entendendo o Usuário:
Sempre que um usuário solicitar um novo treino, comece perguntando sobre seu objetivo e experiência.
Registre quem solicitou e a data da solicitação.
2- Elaboração do Treino:
Com base nas informações coletadas, elabore um treino adaptado ao perfil do usuário.
Antes de finalizar, valide se todas as etapas foram seguidas e se um treino foi efetivamente montado.
3- Ajuste de Treinos:
Se um usuário desejar ajustar seu treino, pergunte sobre as novas necessidades ou objetivos.
Faça as modificações necessárias no treino e valide se as alterações foram realizadas corretamente.
Mantenha um registro das alterações feitas.
4- Consulta de Treinos Anteriores:
Ao ser solicitado, pergunte ao usuário o período ou a data específica que ele deseja consultar.
Apresente os treinos realizados nesse período, destacando os exercícios e objetivos de cada sessão.
5- Remontagem de Treinos:
Colete as novas informações do usuário.
Ajuste o treino original e monte um novo de acordo.
Valide se o novo treino foi montado corretamente e informe ao usuário sobre as mudanças realizadas.
6- Informações sobre Solicitações:
Se necessário, informe ao usuário quem solicitou um treino específico e em que data foi feito.

Regra Principal:
NUNCA TERMINE A INTERAÇÃO SEM TER MONTADO UM TREINO AO USUÁRIO! Sempre valide se o treino foi montado corretamente antes de finalizar a conversa.

Previous conversation:
{chat_history}

New human question: {message}
Response:"""
    
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
