FROM public.ecr.aws/lambda/python:3.10

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# VSCode開発用
RUN yum install -y tar gzip

#localstack用
RUN mkdir /root/.aws
COPY .aws /root/.aws/
COPY localstack_credential.sh /var/task/
RUN source /var/task/localstack_credential.sh

#環境変数をコピー
COPY .env /var/task/

#aws-cliをインストール
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN yum -y install unzip
RUN unzip /var/task/awscliv2.zip
RUN ./aws/install

# Copy function code
# LAMBDA_TASK_ROOTは/var/task
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]