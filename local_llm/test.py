from ollama import Client

client = Client(host='http://localhost:10001')
response = client.generate(
    model='llama3.1:8b-instruct-q8_0',
    prompt="""
<Instructions> As an unbiased reporter, provide a summary on current actions for the legistlation in question.  Ensure the output reads like a newspaper column. If providing insights chronologically ensure they are in proper order by date.  Provide context from the bill text itself if appropriate.  If you do reference form the bill text always include section of the text the reference comes from.  I will provide a current congress, bill number, title, text, and actions.</Instructions>

<Additional Details>
Todays date is {todays.date}.

Current sitting President: Joe Biden

Key action meanings:
"Presented to President" - This means the legistlation has been brought forward to the Presidents office but the legistlation has not yet been signed or vetod.
"Signed by President" - This means the legistlation has been signed by the president and become public law.

</Additional Details>

<Congress>{congress}</Congress>

<Bill Title>{bill title}</Bill Title>

<Bill Number>{bill type}{bill number}</Bill Number>

<Bill Text>
{bill text}
</Bill Text>

<Bill Actions>
{all bill actions}
</Bill Actions>  
""",
)

print(response['response'])