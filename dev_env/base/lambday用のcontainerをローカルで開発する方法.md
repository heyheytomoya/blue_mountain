https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/python-image.html#python-image-instructions
👆から抜粋

ベースはこのフォルダのDockerfileを使用
docker buildをして、そのイメージがそのままlambdaに使える。

* ローカルテスト方法
  docker run --platform linux/amd64 -p 9000:8080 docker-image-name:test　して
  Invoke-WebRequest -Uri "http://localhost:9000/2015-03-31/functions/function/invocations" -Method Post -Body '{}' -ContentType "application/json"
  を実行
* VSCodeで編集
  docker run したあと、dev containerで開発
  https://qiita.com/eiji-noguchi/items/f44e7c7369d0a7ffe681
  👆参照
* デプロイ方法

1. Aws ecrにアクセスしてリポジトリを作る
2. aws --profile kitai ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin *************.ap-northeast-1.amazonaws.com/*repository_name*
3. docker tag **docker-image**:**tag** `<ECRrepositoryUri>`:latest
4. docker push  ************.ap-northeast-1.amazonaws.com/*repository_name*:latest
5. コンテナイメージを書き出したlambda関数を作る
   dockerにattachして開発したものはdocker commit **docker-image-name**:**tag** をしてimageを書き出してから同じことをする

* localstack使用方法
  localstackを使って、ローカル環境にAWSを再現する。

1. https://www.localstack.cloud/  で登録を済ませる。
2. localstack_credentail.shにexport LOCALSTACK_AUTH_TOKEN=(1.で登録して入れたAUTH＿TOKEN) を書いて保存
3. ローカル環境にlocalstackをインストールする（.exeにパスを通す）
4. localstack start -d --network lsでlocalstackを起動
5. docker inspect localstack-main でlocalstackのIPアドレスを確認。(https://docs.localstack.cloud/references/network-troubleshooting/endpoint-url/)
6. 開発するをコンテナを
   docker run --rm -it --dns (4で確認したIPアドレス) --network ls --platform
   linux/amd64 -p 9000:8080 `<image name>`
   で起動する。
7. docker exec -it (containerID) /bin/bashでコンテナに接続
8. localstackで起動したAWS環境に接続する場合は、aws --profile localstack (awsのコマンド) --endpoint-url=http://(4で確認したIP):4566 で接続する
9. boto3を使う場合にはos.environ['AWS_ENDPOINT_URL'] ="http://(4で確認したIP):4566"をスクリプトに追加する
   👆準備したDockerfileをベースにビルドすること
