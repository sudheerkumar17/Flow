from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import pyodbc
import os
import requests

app = Flask(__name__)
CORS(app)

# --- SQL Server Config ---
DB_CONFIG = {
    "server": "SSS2019097PC\\SQLEXPRESS",
    "database": "flow",
    "username": "ssspluser",
    "password": "password123"
}

def get_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};"
        f"PWD={DB_CONFIG['password']}"
    )
    return pyodbc.connect(conn_str)

# --- Serve the frontend HTML file ---
@app.route('/')
def index():
    return send_from_directory(os.getcwd(), 'github_form.html')  # Serve the file from current folder

# --- API endpoint to save GitHub credentials ---
@app.route('/api/save_github', methods=['POST'])
def save_github():
    try:    
        data = request.get_json()
        username = data.get('username')
        access_token = data.get('access_token')

        if not username or not access_token:
            return jsonify({"error": "Both username and access token are required"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO github_credentials (username, access_token, created_at)
            VALUES (?, ?, ?)
        """
        cursor.execute(query, (username, access_token, datetime.now()))
        conn.commit()

        return jsonify({"message": "GitHub credentials saved successfully!"}), 201

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# --- API endpoint to update access token ---
@app.route('/api/update_token', methods=['PUT'])
def update_token():
    try:
        data = request.get_json()
        username = data.get('username')
        new_token = data.get('access_token')

        if not username or not new_token:
            return jsonify({"error": "Both username and new access token are required"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Check if username exists
        check_query = "SELECT COUNT(*) FROM github_credentials WHERE username = ?"
        cursor.execute(check_query, (username,))
        exists = cursor.fetchone()[0]

        if exists == 0:
            return jsonify({"error": f"Username '{username}' not found"}), 404

        # Update the token
        update_query = """
            UPDATE github_credentials
            SET access_token = ?
            WHERE username = ?
        """
        cursor.execute(update_query, (new_token, username))
        conn.commit()

        return jsonify({"message": f"Access token for '{username}' updated successfully!"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

# --- API endpoint to connect GitHub and get repos ---
@app.route('/api/connect_github', methods=['POST'])
def connect_github():
    try:
        data = request.get_json()
        username = data.get('username')

        if not username:
            return jsonify({"error": "Username is required"}), 400

        # 1️⃣ Get access token from DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_token FROM github_credentials WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": f"Username '{username}' not found"}), 404

        access_token = row[0]

        # 2️⃣ Connect to GitHub API using the token
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Fetch user's repositories
        github_response = requests.get("https://api.github.com/user/repos", headers=headers)

        if github_response.status_code != 200:
            return jsonify({
                "error": "Failed to connect to GitHub",
                "details": github_response.json()
            }), github_response.status_code

        repos = github_response.json()
        repo_names = [repo['name'] for repo in repos]

        return jsonify({
            "message": f"Connected to GitHub for user '{username}' successfully",
            "repositories": repo_names
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# --- NEW API endpoint to get branches of a repo ---
@app.route('/api/get_branches', methods=['POST'])
def get_branches():
    try:
        data = request.get_json()
        username = data.get('username')
        repo_name = data.get('repo_name')

        if not username or not repo_name:
            return jsonify({"error": "Username and repo_name are required"}), 400

        # 1️⃣ Get access token from DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_token FROM github_credentials WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": f"Username '{username}' not found"}), 404

        access_token = row[0]

        # 2️⃣ Fetch branches from GitHub
        api_url = f"https://api.github.com/repos/{username}/{repo_name}/branches"
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(api_url, headers=headers)

        if response.status_code != 200:
            return jsonify({
                "error": "Failed to fetch branches",
                "details": response.json()
            }), response.status_code

        branches_data = response.json()
        branch_names = [b['name'] for b in branches_data]

        return jsonify({
            "message": f"Branches for repository '{repo_name}' fetched successfully",
            "repository": repo_name,
            "branches": branch_names
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# --- NEW API endpoint to get files from a selected repo and branch ---
@app.route('/api/get_files', methods=['POST'])
def get_files():
    try:
        data = request.get_json()
        username = data.get('username')
        repo_name = data.get('repo_name')
        branch_name = data.get('branch_name')

        if not username or not repo_name or not branch_name:
            return jsonify({"error": "Username, repo_name, and branch_name are required"}), 400

        # 1️⃣ Get access token from DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_token FROM github_credentials WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": f"Username '{username}' not found"}), 404

        access_token = row[0]

        # 2️⃣ Fetch files from GitHub repo branch
        api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents?ref={branch_name}"
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(api_url, headers=headers)

        if response.status_code != 200:
            return jsonify({
                "error": "Failed to fetch files from GitHub",
                "details": response.json()
            }), response.status_code

        files_data = response.json()

        # 3️⃣ Extract file & folder names
        files = [
            {"name": item["name"], "type": item["type"]}
            for item in files_data
        ]

        return jsonify({
            "message": f"Files for repo '{repo_name}' and branch '{branch_name}' fetched successfully",
            "repository": repo_name,
            "branch": branch_name,
            "files": files
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# --- NEW API endpoint to upload a local Python file to GitHub ---
@app.route('/api/github_upload', methods=['POST'])
def github_upload():
    try:
        username = request.form.get('username')
        repo_name = request.form.get('repo_name')
        branch_name = request.form.get('branch_name')
        file = request.files.get('file')

        if not all([username, repo_name, branch_name, file]):
            return jsonify({"error": "username, repo_name, branch_name, and file are required"}), 400

        # 1️⃣ Get access token from DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_token FROM github_credentials WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": f"Username '{username}' not found in database"}), 404

        access_token = row[0]

        # 2️⃣ Prepare GitHub upload API URL
        file_name = file.filename
        api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_name}"

        # 3️⃣ Read file content and encode in Base64
        import base64
        file_content = base64.b64encode(file.read()).decode('utf-8')

        # 4️⃣ Get the latest commit SHA of the branch (for correct ref)
        branch_url = f"https://api.github.com/repos/{username}/{repo_name}/branches/{branch_name}"
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        branch_resp = requests.get(branch_url, headers=headers)

        if branch_resp.status_code != 200:
            return jsonify({"error": "Failed to fetch branch details", "details": branch_resp.json()}), branch_resp.status_code

        base_commit_sha = branch_resp.json()["commit"]["sha"]

        # 5️⃣ Upload file to GitHub
        payload = {
            "message": f"Upload {file_name} via API",
            "content": file_content,
            "branch": branch_name
        }

        upload_resp = requests.put(api_url, headers=headers, json=payload)

        if upload_resp.status_code not in [200, 201]:
            return jsonify({
                "error": "Failed to upload file to GitHub",
                "details": upload_resp.json()
            }), upload_resp.status_code

        return jsonify({
            "message": f"File '{file_name}' uploaded successfully to repo '{repo_name}' on branch '{branch_name}'",
            "file_url": upload_resp.json().get("content", {}).get("html_url")
        }), 201

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


if __name__ == '__main__':
    app.run(debug=True)
    
    

    
    
    
    
