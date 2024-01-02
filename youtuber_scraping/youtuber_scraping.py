from youtube_transcript_api import YouTubeTranscriptApi
import googleapiclient.discovery
import googleapiclient.errors
from datetime import datetime
from dotenv import load_dotenv
import os
import csv
from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import HuggingFaceBgeEmbeddings
import os
from llama_index.langchain_helpers.text_splitter import TokenTextSplitter
import tiktoken
from langchain.schema import Document
import pandas as pd

#環境変数読み込み
load_dotenv('../.env')

#新しい順からビデオを取り込む
def get_script_date(youtuber_name, channel_id, from_date, youtube):
    print("新しい順に取得")
    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    videos = []
    next_page_token = None
    while True:
        res = youtube.playlistItems().list(playlistId=playlist_id,
                                        part='contentDetails',
                                        maxResults=50,
                                        pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')
        if next_page_token is None:
            break
    
    #日時で指定
    videos = [video for video in videos if datetime.strptime(video['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ") > from_date]
    
    for video in videos:
        # print(video['snippet'])
        video_id = video['snippet']['resourceId']['videoId']
        vidoe_title = video['snippet']['title']
        video_description = video['snippet']['description']
        video_date = video['snippet']['publishedAt']
        print('Fetching subtitles for ', video_id)
        try:
            srt = YouTubeTranscriptApi().get_transcript(video_id, languages=['ja'])
            transcript = '\n'.join([chunk["text"] for chunk in srt])
            
            #字幕から余分な要素を取り除く
            transcript = transcript.replace("[音楽]", "")
            transcript = transcript.replace("\n", "")
            
            #フォルダ作成
            folder_pass = os.path.join(os.getcwd(), "raw_data", youtuber_name)
            if not os.path.exists(folder_pass):
                print("フォルダ作成:", folder_pass)
                os.makedirs(folder_pass)
            save_pass = os.path.join(os.getcwd(), "raw_data", youtuber_name, f'{video_id}.csv')
            with open(save_pass, 'w', encoding='utf-8', newline="") as f:
                writer = csv.writer(f)
                writer.writerows(
                    [['video_id', video_id],
                    ['video_title', vidoe_title],
                    ['video_description', video_description],
                    ['video_date', video_date],
                    ['transcript', transcript]]
                    )
                # writer.writerow([video_id, vidoe_title, video_description, video_date, transcript])
        except Exception as e:
            print('Could not fetch subtitles for ', video_id, ': ', str(e))
        print("処理完了")

#再生回数順で取得(なぜか性格にできない・・・、ずっと昔の動画はチャンネルIDが変わっている影響？)
def get_script_number_of_play(youtuber_name, channel_id, youtube, max_number):
    print("再生回数順に取得")
    # while True:
    res = youtube.search().list(
        channelId=channel_id,
        part='snippet',
        maxResults=max_number,
        order='viewCount'
        ).execute()
    videos = res['items']
    
    for video in videos:
        try:
            video_id = video['id']['videoId']
            vidoe_title = video['snippet']['title']
            video_description = video['snippet']['description']
            video_date = video['snippet']['publishedAt']
            print('Fetching subtitles for ', video_id)
        except Exception as e:
            print("Error ", str(e))
            print(video)
        try:
            srt = YouTubeTranscriptApi().get_transcript(video_id, languages=['ja'])
            transcript = '\n'.join([chunk["text"] for chunk in srt])
            
            #字幕から余分な要素を取り除く
            transcript = transcript.replace("[音楽]", "")
            transcript = transcript.replace("\n", "")
            
            #フォルダ作成
            folder_pass = os.path.join(os.getcwd(), "raw_data", youtuber_name)
            if not os.path.exists(folder_pass):
                print("フォルダ作成:", folder_pass)
                os.makedirs(folder_pass)
            save_pass = os.path.join(os.getcwd(), "raw_data", youtuber_name, f'{video_id}.csv')
            with open(save_pass, 'w', encoding='utf-8', newline="") as f:
                writer = csv.writer(f)
                writer.writerows(
                    [['video_id', video_id],
                    ['video_title', vidoe_title],
                    ['video_description', video_description],
                    ['video_date', video_date],
                    ['transcript', transcript]]
                    )
                # writer.writerow([video_id, vidoe_title, video_description, video_date, transcript])
        
        except Exception as e:
            print('Could not fetch subtitles for ', video_id, ': ', str(e))
        print("処理完了")
        
        
        
def youtuber_scraping():
    """
    Youtuberの字幕データを収集する。
    """
    #環境変数確認
    if os.getenv("YOUTUBE_API") == None:
        print("環境変数が設定されていません。.envの中身と場所を確認してください。")
        return None
    
    else:
        print("youtuberの情報収集を開始します...")
        YOUTUBE_API = os.getenv("YOUTUBE_API")
        #csvからの情報読み取り
        df = pd.read_csv("./youtuber_info.csv")
        youtuber_name = df['youtuber_name'].values.tolist()
        youtuber_id = df['youtuber_id'].values.tolist()
        scraping_method = df['scraping_method'].values.tolist()
        scraping_year = df['scraping_year'].values.tolist()
        scraping_month = df['scraping_month'].values.tolist()
        scraping_date = df['scraping_date'].values.tolist()
        max_number = df['max_number'].values.tolist()
        
        #読み込んだリストからの処理
        for i in range(len(youtuber_name)):
            #youtubeのモジュール読み込み
            youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API)
            if scraping_method[i] == 1:
                get_script_date(
                    youtuber_name=youtuber_name[i],
                    channel_id=youtuber_id[i],
                    from_date=datetime(scraping_year[i], scraping_month[i], scraping_date[i]),
                    youtube=youtube
                    )
            elif scraping_method[i] == 2:
                get_script_number_of_play(
                    youtuber_name=youtuber_name[i],
                    channel_id=youtuber_id[i],
                    youtube=youtube,
                    max_number=max_number[i]
                )
            
            else:
                print("無効な数字が選ばれました！scraping method: 1.新しい順に動画を取得 2.再生回数順に動画を取得")
                break
            # ベクトル化処理
            print("Start vector...")
            # ベクトルを保存するディレクトリ
            vector_folder_path = os.path.join(os.getcwd(), "vector_store", youtuber_name[i])
            
            #FAISSのembeddingを定義
            model_name = model_name="intfloat/multilingual-e5-large"
            # model_kwargs = {'device': 'cuda'} #GPUでembedding
            model_kwargs = {'device': 'cpu'} #CPUでembedding
            hf_embeddings = HuggingFaceBgeEmbeddings(
                model_name = model_name,
                model_kwargs = model_kwargs,
            )
            
            text_splitter = TokenTextSplitter(
                separator=" ",
                chunk_size=128,
                chunk_overlap=20,
                tokenizer=tiktoken.get_encoding("cl100k_base").encode)

            # 取り入れたデータを読み込む
            data_filepath = os.path.join(os.getcwd(), "raw_data", youtuber_name[i])
            data_list = os.listdir(data_filepath)
            raw_data_dict_list = []
            for data in data_list:
                with open(os.path.join(data_filepath, data), mode="r", encoding='utf-8') as f:
                    reader = csv.reader(f)
                    dict_from_csv = {rows[0]: rows[1] for rows in reader}
                    raw_data_dict_list.append(dict_from_csv) # raw_data_dict_listには辞書形式で動画の情報が入っている
            document_list = []
            for raw_data_dict in raw_data_dict_list:
                transcript = raw_data_dict['transcript']
                video_id = raw_data_dict['video_id']
                video_title = raw_data_dict['video_title']
                video_description = raw_data_dict['video_description']
                video_date = raw_data_dict['video_date']
                # 字幕を分割
                split_transcript_list = text_splitter.split_text(transcript)
                for split_transcript in split_transcript_list:
                    document_list.append(Document(
                        page_content=split_transcript,
                        metadata={
                            'video_id':video_id,
                            'video_titile':video_title,
                            'video_description':video_description,
                            'video_date':video_date,
                        }
                    ))
                print('add video_id: ', video_id)
            #FAISSのベクトル化
            print('start faiss vector...')
            faiss_vectorstore = FAISS.from_documents(document_list, embedding=hf_embeddings)
            print('faiss vector complete!')
            if not os.path.exists(os.path.join(vector_folder_path, "faiss")):
                os.makedirs(os.path.join(vector_folder_path, "faiss"))
            faiss_vectorstore.save_local(folder_path=os.path.join(vector_folder_path, "faiss"))
            
if __name__ == '__main__':
    youtuber_scraping()