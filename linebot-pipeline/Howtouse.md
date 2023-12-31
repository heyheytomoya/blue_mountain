# 必要な設定

* **環境変数**
  * LINEBOT_NAME : どの人格を選ぶか。 s3のパスに渡している　いまは'sou_sera'のみ
  * LINE_CHANNEL_ACCESS_TOKEN : LINEのチャンネルアクセストークン
  * OPENAI_KEY : openaiのAPIキー（Azure使う場合は不要）
  * BUCKET_NAME: バケット名
    （上記以外にも👆抜け漏れあるかもしれないです・・・）
* **S3のフォルダ構成**

/(BUCKET_NAME)- pickle    -- (LINEBOT_NAME) -- faiss -- faiss_retriever.pkl
                            └ prompt -- (LINEBOT_NAME) -- template.txt

* **Lambda関数のテスト**

以下のjsonでトライ（最後まで試せてない）

{
  "destination": "Ude66f5fa26175b413b7248bf2c6d1c28",
  "events": [
    {
      "type": "message",
      "message": {
        "type": "text",
        "id": "488516710581404131",
        "quoteToken": "GbT0VA4uoCnyWJfRZ93Li_HStXdWWni-2b5uRExDojomTzxmuYEq4RWZY3r3NkLZCJgOmnha_UqJEs26DDTi4YB1vZSBBjQDCOAJsuQQ9BzkPlAad_vOygwU6drCJQXjbkY_ZDgH1-N5mWD3C6fSrw",
        "text": "おかねが欲しいです"
      },
      "webhookEventId": "01HJZEGX96ZEHWYP9Z3VGESYF2",
      "deliveryContext": {
        "isRedelivery": false
      },
      "timestamp": 1704009954091,
      "source": {
        "type": "user",
        "userId": "U024cbe6f71b9c2d2f088a3c23410917e"
      },
      "replyToken": "77464f3e66b44867acfe21870ac95ad3",
      "mode": "active"
    }
  ]
}

* **Lambda関数設定**
  タイムアウト 15分
  エフェラルストレージとメモリを増やす
  s3へのアクセス許可

#### Future work

* [ ] 会話履歴をDynamoDBに保管
* [ ] ほかの人格を作成
* [ ] LINEの課金システム・・・
