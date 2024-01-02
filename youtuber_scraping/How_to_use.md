# Youtuber情報収集スクリプト

**使い方**

* youtuber_info.csvに必要な情報を入力

  * youtuber_name: youtuberの名前。ディレクトリの名前になる。
  * youtuber_id: チャンネルのID　手動で調べる
  * scraping_method: 情報収集の方法　１は新しい動画順、２はチャンネルの再生回数順になる（だたし、チャンネルIDの関係で完全にYoutubeの結果とは一致しない）
  * scraping_year, month, date: いつからの情報を集めるか。scraping_methodが1の時に有効
  * max_number:動画を集める数、scraping_methodが2の時に有効
* blue_mountainのフォルダに.envを配置。youtube api をYOUTUBE_APIとして指定
* ./youtuber_scrapingをカレントディレクトリにして、python youtuber_scraping.py　で実行。
* ./youtuber_scrapingの下に生の字幕データとベクトルストアのデータが保存される。

  ** 注意点 **
  csvはexcelで編集しないこと！保存の際にエラーになる。

  **Future Work**
* Document listには動画のタイトルと動画の紹介文が入っているので、質問の内容に近い動画タイトルからのデータのみをLLMに渡すと回答の精度が上がるかも？
