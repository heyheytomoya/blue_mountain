FROM public.ecr.aws/lambda/python:3.10
# Copy requirements.txt and function code to /app in the container
COPY requirements.txt ${LAMBDA_TASK_ROOT}
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
RUN pip install --upgrade pip
# Install the specified packages
RUN pip install -r requirements.txt
# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]