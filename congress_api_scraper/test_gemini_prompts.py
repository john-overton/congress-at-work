"""
Install the Google AI Python SDK

$ pip install google-generativeai
"""

import os
import google.generativeai as genai
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keys'))

from keys import gg_key

genai.configure(api_key=gg_key)

#Prompt to use
prompt = "<Instructions> As an unbiased reporter, provide a detailed update on current actions for the legistlation in question.  Ensure the output reads like a newpaper column. If providing insights chronologically ensure they are in proper order by date.  Provide context from the bill text itself if appropriate.  If you do reference form the bill text always include section of the text the reference comes from.  I will provide a current congress, bill number, title, text, and actions.</Instructions>\n\n<Additional Details>\nTodays date is 09/23/2024.\n\nKey action meanings:\n\"Presented to President\" - This means the legistlation has been brought forward to the Presidents office but the legistlation has not yet been signed or vetod.\n\"Signed by President\" - This means the legistlation has been signed by the president and become public law.\n\n</Additional Details>\n\n<Congress>118</Congress>\n\n<Bill Title>Congressional Budget Office Data Sharing Act</Bill Title>\n\n<Bill Number>HR 7032</Bill Number>\n\n<Bill Text>\n[Congressional Bills 118th Congress]\n[From the U.S. Government Publishing Office]\n[H.R. 7032 Received in Senate (RDS)]\n\n<DOC>\n118th CONGRESS\n  2d Session\n                                H. R. 7032\n\n\n_______________________________________________________________________\n\n\n                   IN THE SENATE OF THE UNITED STATES\n\n                             April 30, 2024\n\n                                Received\n\n_______________________________________________________________________\n\n                                 AN ACT\n\n\n \n To amend the Congressional Budget and Impoundment Control Act of 1974 \n to provide the Congressional Budget Office with necessary authorities \nto expedite the sharing of data from executive branch agencies, and for \n                            other purposes.\n\n    Be it enacted by the Senate and House of Representatives of the \nUnited States of America in Congress assembled,\n\nSECTION 1. SHORT TITLE.\n\n    This Act may be cited as the ``Congressional Budget Office Data \nSharing Act''.\n\nSEC. 2. REQUESTS BY CBO OF INFORMATION FROM EXECUTIVE AGENCIES.\n\n    (a) In General.--Section 201(d) of the Congressional Budget and \nImpoundment Control Act of 1974 (2 U.S.C. 601(d)) is amended--\n            (1) by striking ``The Director is authorized'' and \n        inserting ``(1) The Director is authorized'';\n            (2) by striking ``(other than material the disclosure of \n        which would be a violation of law)'' and inserting ``(with or \n        without written agreement) provided that the Director maintains \n        the level of confidentiality required by law of the department, \n        agency, establishment, or regulatory agency or commission from \n        which it is obtained in accordance with section 203(e)''; and\n            (3) by adding at the end the following:\n    ``(2) No provision of law enacted after the date of the enactment \nof the Congressional Budget Office Data Sharing Act shall be construed \nto supersede, limit, or otherwise modify the authority of the Director \nto obtain any material under this subsection unless such provision \nspecifically provides, by specific reference to this paragraph, that \nsuch authority is to be superseded, limited, or otherwise modified.''.\n    (b) Report.--Not later than one year after the date of the \nenactment of this Act, the Director of the Congressional Budget Office \nshall submit, to the chairs of the Committees on the Budget of the \nHouse of Representatives and the Senate, a report listing any request \nfor information pursuant to a written agreement under section 201(d) of \nthe Congressional Budget and Impoundment Control Act of 1974 (2 U.S.C. \n601(d)), as amended by subsection (a) of this Act, made to any \ndepartment, agency, or establishment of the executive branch of \nGovernment or any regulatory agency or commission of the Government and \nany challenges faced accessing information under such section.\n\n            Passed the House of Representatives April 29, 2024.\n\n            Attest:\n\n                                             KEVIN F. MCCUMBER,\n\n                                                                 Clerk.\n</Bill Text>\n\n<Bill Actions>\n118\thr\t7032\t28000\t2024-09-18\tPresented to President.\tPresident\n118\thr\t7032\tE20000\t2024-09-18\tPresented to President.\tFloor\n118\thr\t7032\t\t2024-09-11\tMessage on Senate action sent to the House.\tFloor\n118\thr\t7032\t\t2024-09-10\tPassed Senate without amendment by Unanimous Consent. (consideration: CR S5945-5946)\tFloor\n118\thr\t7032\t17000\t2024-09-10\tPassed/agreed to in Senate: Passed Senate without amendment by Unanimous Consent.\tFloor\n118\thr\t7032\t\t2024-04-30\tReceived in the Senate, read twice.\tIntroReferral\n118\thr\t7032\t5000\t2024-04-29\tReported by the Committee on Budget. H. Rept. 118-474.\tCommittee\n118\thr\t7032\t8000\t2024-04-29\tPassed/agreed to in House: On motion to suspend the rules and pass the bill Agreed to by voice vote. (text: CR H2679)\tFloor\n118\thr\t7032\tH12200\t2024-04-29\tReported by the Committee on Budget. H. Rept. 118-474.\tCommittee\n118\thr\t7032\tH12410\t2024-04-29\tPlaced on the Union Calendar, Calendar No. 393.\tCalendars\n118\thr\t7032\tH30000\t2024-04-29\tConsidered under suspension of the rules. (consideration: CR H2679-2683)\tFloor\n118\thr\t7032\tH30300\t2024-04-29\tMr. Yakym moved to suspend the rules and pass the bill.\tFloor\n118\thr\t7032\tH37300\t2024-04-29\tOn motion to suspend the rules and pass the bill Agreed to by voice vote. (text: CR H2679)\tFloor\n118\thr\t7032\tH38310\t2024-04-29\tMotion to reconsider laid on the table Agreed to without objection.\tFloor\n118\thr\t7032\tH8D000\t2024-04-29\tDEBATE - The House proceeded with forty minutes of debate on H.R. 7032.\tFloor\n118\thr\t7032\tH15000-B\t2024-02-06\tCommittee Consideration and Mark-up Session Held\tCommittee\n118\thr\t7032\tH19000\t2024-02-06\tOrdered to be Reported by the Yeas and Nays: 30 - 0.\tCommittee\n118\thr\t7032\t1000\t2024-01-18\tIntroduced in House\tIntroReferral\n118\thr\t7032\tH11100\t2024-01-18\tReferred to the House Committee on the Budget.\tIntroReferral\n118\thr\t7032\tIntro-H\t2024-01-18\tIntroduced in House\tIntroReferral\n</Bill Actions>"

# Create the model
generation_config = {
  "temperature": 1.00,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

response = model.generate_content(prompt)

print(response.text)