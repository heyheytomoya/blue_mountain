import sys
def handler(event, context):
    return 'Hello from AWS Lambda using Python' + sys.version + '!' + 'Satoshi Kitai test2'