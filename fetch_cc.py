from youtube_transcript_api import YouTubeTranscriptApi
import googleapiclient.discovery
import googleapiclient.errors
from datetime import datetime, timedelta
#APIキーを設定します
api_key = "googleのAPI"
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
channel_id = "UCmMNBtjt6_AjKwC2p0aN8wg"  # チャンネルIDを設定します
from_date = datetime(2023, 11, 20)  # 字幕を取得したい動画の最小投稿日を設定します
def get_channel_videos(channel_id, from_date):
    # 指定したチャンネルから動画のリストを取得します
    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    videos = []
    next_page_token = None
    while True:
        res = youtube.playlistItems().list(playlistId=playlist_id,
                                           part='snippet',
                                           maxResults=50,
                                           pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')
        if next_page_token is None:
            break
    return [video for video in videos if
            datetime.strptime(video['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ") > from_date]
videos = get_channel_videos(channel_id, from_date)
for video in videos:
    video_id = video['snippet']['resourceId']['videoId']
    print('Fetching subtitles for ', video_id)
    try:
        srt = YouTubeTranscriptApi().get_transcript(video_id, languages=['ja'])
        transcript = '\n'.join([chunk["text"] for chunk in srt])
        with open(f'{video_id}.txt', 'w', encoding='utf-8') as f:
            f.write(transcript)
    except Exception as e:
        print('Could not fetch subtitles for ', video_id, ': ', str(e))