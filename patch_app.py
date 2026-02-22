import re

with open("dashboard/app.js", "r") as f:
    code = f.text if hasattr(f, "text") else f.read()

# Add logic to beginning
api_fetch_code = """
let githubToken = localStorage.getItem('githubToken');

async function apiFetch(url, options = {}) {
    if (githubToken) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${githubToken}`;
    }
    return fetch(url, options);
}

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    if (token) {
        githubToken = token;
        localStorage.setItem('githubToken', token);
        window.history.replaceState({}, document.title, window.location.pathname);
    }
"""

code = code.replace("document.addEventListener('DOMContentLoaded', () => {", api_fetch_code, 1)

# Replace fetch(...) with apiFetch(...)
code = re.sub(r'\bfetch\(', 'apiFetch(', code)

with open("dashboard/app.js", "w") as f:
    f.write(code)

