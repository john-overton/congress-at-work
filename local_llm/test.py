from ollama import Client

client = Client(host='http://localhost:10001')
response = client.generate(
    model='llama3.1:8b-instruct-q8_0',
    prompt="""
<Instructions>
I need a one word response that is based on all analysis and context of an active bill and actions.  
The response should be only be "Must Know", "Important", or "Minimal".
ONLY USE ONE WORD.  DO NOT PROVIDE ANY ADDITIONAL CONTEXT.
You are representing the general populace and you should interperate the response based on how much an action and bill impacts the nation, and society.  
You will need take into consideration the full context of the bill and what may be controversial but with an unbiased lens.  
I will provide a current congress, bill number, title, text, and actions.

</Instructions>

<Additional Details>
Todays date is 09/25/2024.

Current sitting President: Joe Biden

Key action meanings:
"Presented to President" - This means the legistlation has been brought forward to the Presidents office but the legistlation has not yet been signed or vetod.
"Signed by President" - This means the legistlation has been signed by the president and become public law.

</Additional Details>

<Congress>
118

</Congress>

<Bill Title>
Congressional Budget Office Data Sharing Act

</Bill Title>

<Bill Number>
HR 7032

</Bill Number>

<Bill Text>
[Congressional Bills 118th Congress]
[From the U.S. Government Publishing Office]
[H.R. 7032 Received in Senate (RDS)]

<DOC>
118th CONGRESS
  2d Session
                                H. R. 7032


_______________________________________________________________________


                   IN THE SENATE OF THE UNITED STATES

                             April 30, 2024

                                Received

_______________________________________________________________________

                                 AN ACT


 
 To amend the Congressional Budget and Impoundment Control Act of 1974 
 to provide the Congressional Budget Office with necessary authorities 
to expedite the sharing of data from executive branch agencies, and for 
                            other purposes.

    Be it enacted by the Senate and House of Representatives of the 
United States of America in Congress assembled,

SECTION 1. SHORT TITLE.

    This Act may be cited as the ``Congressional Budget Office Data 
Sharing Act''.

SEC. 2. REQUESTS BY CBO OF INFORMATION FROM EXECUTIVE AGENCIES.

    (a) In General.--Section 201(d) of the Congressional Budget and 
Impoundment Control Act of 1974 (2 U.S.C. 601(d)) is amended--
            (1) by striking ``The Director is authorized'' and 
        inserting ``(1) The Director is authorized'';
            (2) by striking ``(other than material the disclosure of 
        which would be a violation of law)'' and inserting ``(with or 
        without written agreement) provided that the Director maintains 
        the level of confidentiality required by law of the department, 
        agency, establishment, or regulatory agency or commission from 
        which it is obtained in accordance with section 203(e)''; and
            (3) by adding at the end the following:
    ``(2) No provision of law enacted after the date of the enactment 
of the Congressional Budget Office Data Sharing Act shall be construed 
to supersede, limit, or otherwise modify the authority of the Director 
to obtain any material under this subsection unless such provision 
specifically provides, by specific reference to this paragraph, that 
such authority is to be superseded, limited, or otherwise modified.''.
    (b) Report.--Not later than one year after the date of the 
enactment of this Act, the Director of the Congressional Budget Office 
shall submit, to the chairs of the Committees on the Budget of the 
House of Representatives and the Senate, a report listing any request 
for information pursuant to a written agreement under section 201(d) of 
the Congressional Budget and Impoundment Control Act of 1974 (2 U.S.C. 
601(d)), as amended by subsection (a) of this Act, made to any 
department, agency, or establishment of the executive branch of 
Government or any regulatory agency or commission of the Government and 
any challenges faced accessing information under such section.

            Passed the House of Representatives April 29, 2024.

            Attest:

                                             KEVIN F. MCCUMBER,

                                                                 Clerk.

</Bill Text>

<Bill Actions>
118	hr	7032	28000	2024-09-18	Presented to President.	President
118	hr	7032	E20000	2024-09-18	Presented to President.	Floor
118	hr	7032		2024-09-11	Message on Senate action sent to the House.	Floor
118	hr	7032		2024-09-10	Passed Senate without amendment by Unanimous Consent. (consideration: CR S5945-5946)	Floor
118	hr	7032	17000	2024-09-10	Passed/agreed to in Senate: Passed Senate without amendment by Unanimous Consent.	Floor
118	hr	7032		2024-04-30	Received in the Senate, read twice.	IntroReferral
118	hr	7032	5000	2024-04-29	Reported by the Committee on Budget. H. Rept. 118-474.	Committee
118	hr	7032	8000	2024-04-29	Passed/agreed to in House: On motion to suspend the rules and pass the bill Agreed to by voice vote. (text: CR H2679)	Floor
118	hr	7032	H12200	2024-04-29	Reported by the Committee on Budget. H. Rept. 118-474.	Committee
118	hr	7032	H12410	2024-04-29	Placed on the Union Calendar, Calendar No. 393.	Calendars
118	hr	7032	H30000	2024-04-29	Considered under suspension of the rules. (consideration: CR H2679-2683)	Floor
118	hr	7032	H30300	2024-04-29	Mr. Yakym moved to suspend the rules and pass the bill.	Floor
118	hr	7032	H37300	2024-04-29	On motion to suspend the rules and pass the bill Agreed to by voice vote. (text: CR H2679)	Floor
118	hr	7032	H38310	2024-04-29	Motion to reconsider laid on the table Agreed to without objection.	Floor
118	hr	7032	H8D000	2024-04-29	DEBATE - The House proceeded with forty minutes of debate on H.R. 7032.	Floor
118	hr	7032	H15000-B	2024-02-06	Committee Consideration and Mark-up Session Held	Committee
118	hr	7032	H19000	2024-02-06	Ordered to be Reported by the Yeas and Nays: 30 - 0.	Committee
118	hr	7032	1000	2024-01-18	Introduced in House	IntroReferral
118	hr	7032	H11100	2024-01-18	Referred to the House Committee on the Budget.	IntroReferral
118	hr	7032	Intro-H	2024-01-18	Introduced in House	IntroReferral

</Bill Actions>    
""",
)

print(response['response'])