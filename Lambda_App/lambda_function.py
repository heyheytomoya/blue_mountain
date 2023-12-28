import os

os.environ["TRANSFORMERS_CACHE"] = "/tmp/huggingface_cache/"
os.environ["HF_HOME"] = "/tmp/huggingface_cache/"
os.environ["HF_DATASETS_CACHE"] = "/tmp/huggingface_cache/"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/huggingface_cache/"
os.environ["TORCH_HOME"] = "/tmp/huggingface_cache/"

import json
import boto3
from langchain.memory.buffer import ConversationBufferMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.schema.messages import get_buffer_string
from langchain.schema.output_parser import StrOutputParser
from operator import itemgetter
from langchain.chat_models import AzureChatOpenAI
from langchain.globals import set_debug
from langchain.globals import set_verbose
from langchain.retrievers import EnsembleRetriever
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
import uuid
from langchain.callbacks.base import BaseCallbackHandler
from langchain.vectorstores.faiss import FAISS
from langchain.retrievers import TFIDFRetriever
from langchain.embeddings import HuggingFaceBgeEmbeddings
from linebot import LineBotApi
from linebot.models import TextSendMessage


# debug
# Langchainのverboseとdebugを有効にする
set_verbose(True)
set_debug(True)

# llmの設定
llm = AzureChatOpenAI(
    azure_endpoint=os.environ.get("API_ENDPOINT"),
    deployment_name=os.environ.get("DEPLOYMENT_NAME"),
    openai_api_version=os.environ.get("API_VERSION"),
    openai_api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    streaming=True
)

# 環境変数からLINE Botのチャネルアクセストークンを取得
LINE_CHANNEL_ACCESS_TOKEN = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
# チャネルアクセストークンを使用して、LineBotApiのインスタンスを作成
LINE_BOT_API = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

print('llm', llm)

# S3クライアントのセットアップ
s3 = boto3.client('s3')

# ダウンロード元のS3バケット名とプレフィックス（フォルダ）を指定
s3_bucket_name = 'vectorstore-buruman'

# ダウンロード先の一時ディレクトリを指定（Lambda関数内では一時的なファイル保存先として利用）
local_temp_directory = '/tmp/'

# vectorstoreファイルのダウンロード処理
for s3_folder_prefix in ['faiss/', 'tfid/']:
    s3_objects = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=s3_folder_prefix)
    for obj in s3_objects.get('Contents', []):
        s3_object_key = obj['Key']
        local_file_path = os.path.join(local_temp_directory, os.path.basename(s3_object_key))
        s3.download_file(s3_bucket_name, s3_object_key, local_file_path)

#FAISSのembedding
model_name = model_name="intfloat/multilingual-e5-large"
# model_kwargs = {'device': 'cuda'} #GPUでembedding
model_kwargs = {'device': 'cpu'} #CPUでembedding
hf_embeddings = HuggingFaceBgeEmbeddings(
    model_name = model_name,
    model_kwargs = model_kwargs,
)

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

#retrieverのロード
faiss_retriever = FAISS.load_local("/tmp", hf_embeddings)
# tfid_retriever = TFIDFRetriever.load_local("/tmp")

# tfid_retriever.k=4
faiss_retriever = faiss_retriever.as_retriever(search_kwargs={"k": 4})
run_manager = CallbackManagerForRetrieverRun(run_id=uuid.uuid4, handlers=[BaseCallbackHandler()], inheritable_handlers=[BaseCallbackHandler()])

# initialize the ensemble retriever
ensemble_retriever = EnsembleRetriever(
    retrievers=[
                # tfid_retriever,
                faiss_retriever],
                weights=[1.0]
)

_template = """
以下のチャットの履歴から次の質問をAIが検索しやすいように言い換えてから会話を続けてください。
チャットの履歴:
{chat_history}
次の質問:
{question}
言い換えられた独立した質問:"""

question_prompt = PromptTemplate.from_template(_template)

template = """
【役割】
* あなたは宋世羅の知識を持ったAIです。
* 彼は早稲田大学人間科学部を卒業後、野村證券に入社し、証券営業マンとして4年間勤務しました。その後、独立して現在はフルコミッション（完全歩合制）の保険営業マンとして活動しています。
* 宋世羅さんは自身の経験に基づくお金に関する情報、特に「保険」、「株」、「投資信託」、「貯金」、「営業」、「投資をする際の考え方」などについて発信しています。
* 以下は彼の発言の一部です。この発言の内容から、参考になる情報があればそれをベースに質問に答えてください。
* もし参考になる情報がなければ、お金儲けを第一に考える意識高いYoutuberとして答えてください。。
* 回答の際にはほかの人を見下すような態度で答えてください。回答の際は「私」を主語にしてください。
* 回答の際には、彼の発言から口調を真似て回答してください。
* 答えは日本語でお願いします。あなたは巨大な自尊心を持っています。自信をもって簡潔に答えてください。

宋世羅の発言：
{context}

質問 : {question}"""

answer_prompt = ChatPromptTemplate.from_template(template)

memory_toyotaimzu = ConversationBufferMemory(
    return_messages=True,
    output_key="answer",
    input_key="question"
)

loaded_memory = RunnablePassthrough.assign(
    chat_history=RunnableLambda(memory_toyotaimzu.load_memory_variables) | itemgetter("history"),
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
    "docs": itemgetter("standalone_question") | ensemble_retriever,
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

def lambda_handler(event, context):
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

                answer_prompt = ChatPromptTemplate.from_template(template)

                memory_toyotaimzu = ConversationBufferMemory(
                    return_messages=True,
                    output_key="answer",
                    input_key="question"
                )

                loaded_memory = RunnablePassthrough.assign(
                    chat_history=RunnableLambda(memory_toyotaimzu.load_memory_variables) | itemgetter("history"),
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
                    "docs": itemgetter("standalone_question") | ensemble_retriever,
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

                # クエリの取得
                # query = event['queryStringParameters']['query']
                
                # Langchainを実行
                raw_result = final_chain.invoke({"question": query})

                # docsを辞書のリストに変換
                # docs_as_dicts = [document_to_dict(doc) for doc in raw_result['docs']]

                # AIMessageからcontent属性を取得してレスポンスとして設定
                result = {
                    'answer': raw_result['answer'].content,  # ここを修正
                    # 'docs': docs_as_dicts
                }

                messageText = result['answer']

                print('リザルト',result)
                print('メッセージ', messageText)
                
                # # 結果をレスポンスとして返す
                # response = {
                #     'statusCode': 200,
                #     'body': result
                # }
                
                # return response
                # メッセージを返信（受信メッセージをそのまま返す）
                LINE_BOT_API.reply_message(replyToken, TextSendMessage(text=messageText))
                return {'statusCode': 200, 'body': json.dumps('Reply ended normally.')}

    except Exception as e:
        # エラーが発生した場合の処理
        response = {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

        return response