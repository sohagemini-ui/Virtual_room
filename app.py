import os
import pickle
import requests
from flask import Flask, request, render_template_string
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

app = Flask(__name__)

# আপলোড করা ছবি সাময়িকভাবে বা স্থায়ীভাবে সেভ করার ফোল্ডার
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Google Photos API Scope
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.appendonly']

def get_google_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
        if creds:
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    return creds

# ফ্রন্টএন্ড ডিজাইন (Virtual Room & Image Tool UI)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>Virtual Room - Image & Source Hub</title>
    <style>
        body { font-family: sans-serif; background: #060a13; color: #fff; text-align: center; padding: 30px; }
        .empire-card { background: rgba(10, 17, 31, 0.85); border: 1px solid rgba(255, 215, 0, 0.3); padding: 30px; border-radius: 20px; max-width: 600px; margin: 0 auto; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h2 { color: #ffd700; }
        input[type="file"] { margin: 20px 0; color: #ffd700; }
        .btn { background: #ffd700; color: #000; padding: 12px 24px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 5px; text-decoration: none; display: inline-block; }
        .result-box { margin-top: 20px; text-align: left; background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 4px solid #ffd700; }
        a { color: #00ffcc; text-decoration: none; }
    </style>
</head>
<body>
    <div class="empire-card">
        <h2>🏛️ Virtual Room : Image Hub</h2>
        <p>ভার্চুয়াল রুমে ছবি আপলোড করুন এবং গুগল ফটোজে বা সোর্স খুঁজুন</p>
        
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="image" accept="image/*" required><br>
            <button type="submit" name="action" value="search" class="btn">🔍 ছবির সোর্স খুঁজুন</button>
            <button type="submit" name="action" value="upload" class="btn">☁️ Google Photos-এ পাঠান</button>
        </form>
        
        {% if message %}
            <div class="result-box">
                <h3>ফলাফল:</h3>
                <p>{{ message | safe }}</p>
                {% if link %}
                    <p>🔗 <a href="{{ link }}" target="_blank">লিংকটি দেখতে এখানে ক্লিক করুন</a></p>
                {% endif %}
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def virtual_room():
    message = None
    link = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        file = request.files.get('image')
        
        if file:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            if action == 'search':
                # সোর্স ফাইন্ডার বা রিভার্স ইমেজ সার্চ লজিক
                message = f"সফলভাবে ফাইলটি ভার্চুয়াল রুমে সেভ করা হয়েছে: <b>{filename}</b>। রিভার্স ইমেজ সার্চ এপিআই (যেমন SerpApi) কানেক্ট করে এর ইন্টারনেট সোর্স ট্র্যাক করা যাবে।"
                
            elif action == 'upload':
                # Google Photos API আপলোড লজিক
                creds = get_google_credentials()
                if creds:
                    upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
                    headers = {
                        'Authorization': 'Bearer ' + creds.token,
                        'Content-type': 'application/octet-stream',
                        'X-Goog-Upload-File-Name': filename,
                        'X-Goog-Upload-Protocol': 'raw',
                    }
                    
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                        
                    response = requests.post(upload_url, headers=headers, data=image_data)
                    upload_token = response.text
                    
                    create_url = 'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate'
                    create_headers = {
                        'Authorization': 'Bearer ' + creds.token,
                        'Content-type': 'application/json',
                    }
                    create_body = {
                        "newMediaItems": [
                            {
                                "description": "Uploaded via Virtual Room App",
                                "simpleMediaItem": {"uploadToken": upload_token}
                            }
                        ]
                    }
                    
                    res = requests.post(create_url, headers=create_headers, json=create_body)
                    res_json = res.json()
                    
                    try:
                        item = res_json['newMediaItemResults'][0]['mediaItem']
                        link = item['productUrl']
                        message = "✅ ছবি সফলভাবে Google Photos-এ আপলোড করা হয়েছে!"
                    except KeyError:
                        message = f"❌ আপলোড করতে সমস্যা হয়েছে: {res_json}"
                else:
                    message = "❌ Google Authentication সফল হয়নি! credentials.json ফাইলটি চেক করুন।"

    return render_template_string(HTML_TEMPLATE, message=message, link=link)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
