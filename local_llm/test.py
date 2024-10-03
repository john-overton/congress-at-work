from ollama import Client

client = Client(host='http://localhost:10001')
response = client.generate(
    model='llama3.2:latest',
    prompt="""Hi How are you?
""",
)

print(response['response'])