import re
with open("dashboard/server.py", "r") as f:
    content = f.read()

# Make _gh_headers take self and use Authorization header
content = content.replace("def _gh_headers() -> dict[str, str]:", "def _gh_headers(self) -> dict[str, str]:")
content = content.replace("token = _gh_token()", """auth_header = self.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    else:
        token = _gh_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers
    
    # We will remove token = _gh_token() replacement below""")

with open("dashboard/server_patched.py", "w") as f:
    f.write(content)
