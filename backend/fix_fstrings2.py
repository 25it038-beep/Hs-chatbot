#!/usr/bin/env python3
"""Fix f-string issues in nvidia_api.py"""

import re

with open('app/api/nvidia_api.py', 'r') as f:
    content = f.read()

# Fix pattern 1: '\n\n' + variable
# Replace: yield f"data: {json.dumps({'type': 'content', 'content': '\n\n' + var})}\n\n"
# With: content_sep = '\n\n' + var; yield f"data: {json.dumps({'type': 'content', 'content': content_sep})}\n\n"

# Pattern to match yield statements with '\n\n' +  variable
pattern1 = r"(\s+)yield f\"data: \{json\.dumps\(\{'type': 'content', 'content': '\\n\\n' \+ (\w+)\}\)\}\\n\\n\""
replacement1 = r"\1content_sep = '\n\n' + \2\n\1yield f\"data: {{json.dumps({{'type': 'content', 'content': content_sep}})}}\n\n\""

content = re.sub(pattern1, replacement1, content)

# Fix pattern 2: nested f-strings with backslashes
# Replace: yield f"data: {json.dumps({'type': 'error', 'content': f'...'})}\n\n"
pattern2 = r"yield f\"data: \{json\.dumps\(\{'type': 'error', 'content': f'([^']+)'\}\)\}\\n\\n\""
replacement2 = r"error_msg = f'\1'\n            yield f\"data: {{json.dumps({{'type': 'error', 'content': error_msg}})}}\n\n\""

content = re.sub(pattern2, replacement2, content)

# Write back the fixed content
with open('app/api/nvidia_api.py', 'w') as f:
    f.write(content)

print("✅ Fixed f-string patterns")

# Verify syntax
import ast
try:
    ast.parse(content)
    print("✅ File is syntactically valid!")
except SyntaxError as e:
    print(f"❌ Still has SyntaxError at line {e.lineno}: {e.msg}")
    print(f"   Text: {e.text}")
