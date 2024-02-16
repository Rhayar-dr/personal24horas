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
        cursor.execute('''CREATE TABLE IF NOT EXISTS numeros_desabilitados
                          (number TEXT)''')

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
    
def check_number_disabled(number):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT number FROM numeros_desabilitados WHERE number=?", (number,))
        return cursor.fetchone() is not None

def disable_number(number):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO numeros_desabilitados (number) VALUES (?)", (number,))

@app.route('/disable-number', methods=['POST'])
def post_disable_number():
    data = request.get_json()
    number = data.get('number', '')
    if number:
        disable_number(number)
        return jsonify({"message": "Número desabilitado com sucesso."}), 200
    else:
        return jsonify({"error": "Número não fornecido."}), 400

@app.route('/bot', methods=['POST'])
def bot_response():
    
    #data = request.get_json() #para teste interno
    #number = data.get('From', '') #para teste interno
    #message = data.get('Body', '') #para teste interno
    number = request.form.get('From', '')
    message = request.form.get('Body', '')

    if check_number_disabled(number):
        return '', 204  # Número desabilitado, retorna 204 No Content

    add_message_to_db(number, message, "human")

    # Logic to fetch previous chat history, run the model, and generate response
    prev_messages = get_messages_from_db(number)
    chat_history = "\n".join([msg[0] for msg in prev_messages])

    template = f"""Voce é Antonella, uma vendedora experiente da Virtual Genius.
Seu objetivo é vender nossos serviços, ser sucinta sem precisar explicar muito, mantenha a conversa com poucas palavras mas acertivas e objetivas, foco para manter no máximo parágrafo por resposta e também caso o cliente queira algo mais personalizado descobrir o que ele quer e oferecer alternativas para ele através de nossos serviços. 
Serviços que oferecemos:
Pacote Básico (Startup IA) Chatbot IA básico para atendimento ao cliente (integração com WhatsApp e website). Relatórios automáticos simples com Power BI. Armazenamento de dados básico em cloud. Suporte técnico padrão. Preço: A partir de R$ 800 por mês.

Pacote Intermediário (Negócio Inteligente) Chatbot IA avançado com personalização moderada. Desenvolvimento de dashboards personalizados com Power BI. Armazenamento e gestão de dados em cloud com configurações de segurança avançadas. Desenvolvimento de scripts básicos em Python para análise de dados. Suporte técnico avançado. Preço: A partir de R$ 1200 por mês.

Pacote Premium (Parceiro de IA) Chatbot IA totalmente personalizado com integração de sistemas complexos. Desenvolvimento e manutenção de dashboards avançados com Power BI. Soluções de armazenamento e ingestão de dados em cloud de alta volumetria. Desenvolvimento personalizado com Python para análise de dados avançada e automação de processos. Suporte técnico prioritário 24/7. Preço: A partir de R$ 1.800 por mês.

Pacote Elite: (Elite IA) Assistente virtual IA de última geração com capacidades avançadas de aprendizado e adaptação, integrando-se perfeitamente a diversos sistemas empresariais. Consultoria e desenvolvimento personalizado de dashboards de Business Intelligence com Power BI, incluindo análises preditivas e prescritivas. Soluções de armazenamento de dados em cloud de alto desempenho, com opções de backup e recuperação de desastres Desenvolvimento e implementação de soluções de análise de dados avançadas com Python, incluindo machine learning e automação de processos complexos. Consultoria estratégica em IA, ajudando na transformação digital e na otimização de processos de negócios. Suporte técnico VIP com atendimento prioritário e dedicado. Preço: A partir de R$ 2.500 por mês.

Caso o cliente queira agendar uma reunião presencial ou online:
Incentive agendamentos para discussões detalhadas através de https://calendly.com/virtualgenius, promovendo um atendimento exclusivo.

Caso exista dados depois de Previous conversation não é preciso dar saudações.

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
