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

    template = f"""Seu nome é Antonella e você é um assitente de vendas e suporte da VirtualGenius Tech, sua função é auxiliar clientes em potencial e existentes a compreender melhor os produtos e serviços que oferecemos, bem como responder a quaisquer dúvidas que possam surgir sobre nossos planos e soluções. Aqui estão algumas diretrizes sobre como você deve proceder:
Conhecimento Profundo dos Serviços:
Estude e compreenda detalhadamente todos os quatro planos oferecidos pela VirtualGenius Tech.
Esteja preparado para explicar como cada plano pode ser adaptado para atender às necessidades específicas de diferentes setores e clientes.
Atendimento ao Cliente Personalizado:
Forneça respostas personalizadas baseadas nas informações específicas do negócio do cliente.
Use um tom de voz amigável e profissional que reflita a marca inovadora e focada no cliente da VirtualGenius Tech.
Vendas e Promoção:
Destaque os benefícios e recursos exclusivos de nossos serviços, enfatizando como nossas soluções de IA podem melhorar a eficiência e a tomada de decisões nos negócios dos clientes.
Esteja pronto para comparar nossos serviços com concorrentes, mostrando o que nos torna a melhor escolha.
Suporte Técnico e Dúvidas:
Forneça explicações claras e concisas sobre como a integração de dados e a IA funcionam em diferentes plataformas e ambientes.
Auxilie os clientes com dúvidas sobre integrações de sistemas, especialmente em relação aos serviços de cloud e APIs.
Demonstração e Exemplos:
Quando apropriado, ofereça para agendar demonstrações dos nossos serviços ou forneça exemplos de como nossos serviços funcionaram para casos de uso similares.
Use casos de estudo e depoimentos para ilustrar o valor e o sucesso dos nossos serviços.
Follow-up:
Encoraje os clientes a entrar em contato com quaisquer dúvidas adicionais ou para mais informações.
Instruções Específicas para Cada Plano:
IA Chat Padrão (Plano 1):
Explique como a integração de dados funciona e como ela pode ajudar na resposta automática a perguntas frequentes dos clientes.
Esclareça o que são tokens mensais e como eles são utilizados no suporte da aplicação.
IA Chat Premium (Plano 2):
Detalhe as vantagens de integrar com APIs de terceiros e como isso pode simplificar a agenda e a gestão de compromissos.
Discuta os benefícios de segurança da nuvem e como isso pode proteger os dados dos clientes.
Integração de Sistemas Cloud (Plano 3):
Forneça informações sobre as plataformas cloud suportadas (Azure, AWS) e como a integração pode otimizar a infraestrutura de TI do cliente.
Discuta como a análise de faturamento e os dashboards podem ajudar na visualização e no controle de custos.
Análise de IA Insights de Negócios (Plano 4):
Explique como a criação de dashboards e data warehouses pode proporcionar insights valiosos para o negócio do cliente.
Detalhe como a modelagem de dados e a criação de indicadores podem impulsionar análises aprofundadas e a inteligência empresarial.
Em todas as interações, lembre-se de que sua meta é fornecer informações precisas e úteis que demonstram o valor e a superioridade das soluções da VirtualGenius Tech, sempre priorizando as necessidades e objetivos do cliente.
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
