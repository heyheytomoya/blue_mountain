
import json
import boto3
from langchain.memory.buffer import ConversationBufferMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.schema.messages import get_buffer_string
from langchain.schema.output_parser import StrOutputParser
from operator import itemgetter
# from langchain.chat_models import AzureChatOpenAI
from langchain.chat_models import ChatOpenAI
from langchain.globals import set_debug
from langchain.globals import set_verbose
# from langchain.retrievers import EnsembleRetriever
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
import uuid
from langchain.callbacks.base import BaseCallbackHandler
from langchain.vectorstores.faiss import FAISS
from langchain.retrievers import TFIDFRetriever
from langchain.embeddings import HuggingFaceBgeEmbeddings
from linebot import LineBotApi
from linebot.models import TextSendMessage
import time
import pickle
from dotenv import load_dotenv
import os
TEMP_FOLDER = '/tmp'
DOWNLOAD_PATH = '/tmp/'
BUCKET_NAME = 'linebot-data'
PICKLE_FILE_NAME = 'faiss_retriver.pkl'
PROMPT_FILE_NAME = 'template.txt'
#LLMの環境変数
load_dotenv('./.env')
#LINEBOTの設定
# 環境変数からLINE Botのチャネルアクセストークンを取得
LINE_CHANNEL_ACCESS_TOKEN = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
# チャネルアクセストークンを使用して、LineBotApiのインスタンスを作成
LINE_BOT_API = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
# debug
# Langchainのverboseとdebugを有効にする
set_verbose(True)
set_debug(True)
#llm定義
# llm = AzureChatOpenAI(
#     azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
#     deployment_name=os.environ.get("DEPLOYMENT_NAME"),
#     openai_api_version=os.environ.get("API_VERSION"),
#     openai_api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
# )
llm = ChatOpenAI(
    openai_api_key = os.environ.get("OPENAI_KEY")
)
#人格定義
LINEBOT_NAME = os.environ.get('LINEBOT_NAME')
#s3からpickle化したretrivalをダウンロード
def downloadS3() :
    print("Download data function.")
    # ベクトルストアのデータ
    # コールドホット判別用にファイルの有無確認
    if os.path.isfile(os.path.join(TEMP_FOLDER, PICKLE_FILE_NAME)):
        print("pickle already exist. pass download...")
    # ファイルが無いときにはダウンロードする
    else:
        print("Download pickle session.")
        # session = boto3.session.Session(profile_name='bluemountain')
        s3_client = boto3.client('s3')
        s3_object_key = os.path.join('pickle', LINEBOT_NAME, 'faiss', PICKLE_FILE_NAME)
        print("Start download pickle.")
        start = time.time()
        s3_client.download_file(BUCKET_NAME, s3_object_key, os.path.join(DOWNLOAD_PATH, PICKLE_FILE_NAME))
        end = time.time()
        print("Download pickle comlete!")
        print(f"Download time {end-start}")
    # promptのデータ
    # コールドホット判別用にファイルの有無確認
    if os.path.isfile(os.path.join(TEMP_FOLDER, PROMPT_FILE_NAME)):
        print("template already exist. pass download...")
    else:
        print("Download template session.")
        session = boto3.session.Session(profile_name='bluemountain')
        s3_client = session.client('s3')
        s3_object_key = os.path.join('prompt', LINEBOT_NAME, PROMPT_FILE_NAME)
        print("Start download template.")
        start = time.time()
        s3_client.download_file(BUCKET_NAME, s3_object_key, os.path.join(DOWNLOAD_PATH, PROMPT_FILE_NAME))
        end = time.time()
        print("Download prompt comlete!")
        print(f"Download time {end-start}")
        
def LCEL(memory, question_prompt, llm, retriever, answer_prompt):
    
    #documentのリストを一つの文にする
    def doclist_to_str(doclist) -> str:
        """ドキュメントのリストを文字列にする
        Args:
            doclist (documentlist): ドキュメントのリスト
        Returns:
            str: 文字列
        """
        result = ""
        for doc in doclist:
            result += doc.page_content
            result += "\n\n"
        return result
    
    loaded_memory = RunnablePassthrough.assign(
        chat_history=RunnableLambda(memory.load_memory_variables) | itemgetter("history"),
    )
    standalone_question = {
        "standalone_question": {
            "question": lambda x: x["question"],
            "chat_history": lambda x: get_buffer_string(x["chat_history"]),
        }
        | question_prompt
        | llm
        | StrOutputParser()
    }
    retrieved_documents = {
        "docs": itemgetter("standalone_question") | retriever,
        "question": lambda x: x["standalone_question"],
    }
    final_inputs = {
        "context": lambda x: doclist_to_str(x["docs"]),
        "question": itemgetter("question"),
    }
    answer = {
        "answer": final_inputs | answer_prompt | llm,
        "docs": itemgetter("docs"),
    }
    
    final_chain = loaded_memory | standalone_question | retrieved_documents | answer
    
    return final_chain
        
# pickleを読み込んで
def read_pickle(query : str) -> str:
    print("Read pickle function.")
    start = time.time()
    with open(os.path.join(DOWNLOAD_PATH, PICKLE_FILE_NAME), 'rb') as f:
        faiss_retriver = pickle.load(f)
    end = time.time()
    print(f"Load pickle model time: {end-start}")
    
    with open(os.path.join(DOWNLOAD_PATH, PROMPT_FILE_NAME), 'r', encoding='utf-8') as f:
        template = f.read()
        print(template)
    
    faiss_retriever = faiss_retriver.as_retriever(search_kwargs={"k": 4})
    run_manager = CallbackManagerForRetrieverRun(run_id=uuid.uuid4, handlers=[BaseCallbackHandler()], inheritable_handlers=[BaseCallbackHandler()])
    
    #会話履歴用のPromptTemplate
    _template = """
    以下のチャットの履歴から次の質問をAIが検索しやすいように言い換えてから会話を続けてください。
    チャットの履歴:
    {chat_history}
    次の質問:
    {question}
    言い換えられた独立した質問:"""
    question_prompt = PromptTemplate.from_template(_template)
    
    #人格形成プロンプト
    answer_prompt = ChatPromptTemplate.from_template(template)
    
    #memory(DynamoDBから読み込み予定。今は暫定)
    memory = ConversationBufferMemory(
    return_messages=True,
    output_key="answer",
    input_key="question"
    )
    
    # LCEL
    answer = LCEL(memory=memory, question_prompt=question_prompt, llm=llm, retriever=faiss_retriever, answer_prompt=answer_prompt).invoke({"question": query})
    result = answer['answer'].content
    return result
def handler(event, context):
    try:
        print('イベント内容',event)
        # LINEからメッセージを受信
        if event['events'][0]['type'] == 'message':
            # メッセージタイプがテキストの場合
            if event['events'][0]['message']['type'] == 'text':
                # リプライ用トークン
                replyToken = event['events'][0]['replyToken']
                # 受信メッセージ
                query = event['events'][0]['message']['text']
                print("query: ", query)
                #AI返答処理
                print("start function")
                downloadS3()
                result = read_pickle(query)
                print("返答内容 :", result)
                LINE_BOT_API.reply_message(replyToken, TextSendMessage(text=result))
                return {'statusCode': 200, 'body': json.dumps('Reply ended normally.')}
        
    # エラーが発生した場合の処理  
    except Exception as e:
        response = {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
        return response