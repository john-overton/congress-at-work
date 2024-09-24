import re

def convert_bold_to_unicode(text):
    # Define Unicode range for bold letters and numbers
    bold_map = {chr(ord('A') + i): chr(0x1D400 + i) for i in range(26)}  # Uppercase
    bold_map.update({chr(ord('a') + i): chr(0x1D41A + i) for i in range(26)})  # Lowercase
    bold_map.update({chr(ord('0') + i): chr(0x1D7CE + i) for i in range(10)})  # Numbers

    def replace_bold(match):
        return ''.join(bold_map.get(c, c) for c in match.group(1))

    # Replace bold text
    return re.sub(r'<b>(.*?)</b>', replace_bold, text)

# Read input file
input_file = 'paste.txt'
with open(input_file, 'r', encoding='utf-8') as file:
    content = file.read()

# Convert bold text
converted_text = convert_bold_to_unicode(content)

# Write output to a new file
output_file = 'twitter_ready_text.txt'
with open(output_file, 'w', encoding='utf-8') as file:
    file.write(converted_text)

print(f"Conversion complete. Output written to {output_file}")