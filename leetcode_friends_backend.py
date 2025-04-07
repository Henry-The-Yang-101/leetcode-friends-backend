from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Home endpoint rendering an HTML template
@app.route('/')
def home():
    return render_template('index.html')

# Example endpoint for sending a friend request
@app.route('/friend_request', methods=['POST'])
def friend_request():
    # Process the request data (this is just a placeholder)
    data = request.get_json()  
    # Normally, you would handle the friend request logic here
    return jsonify({"message": "Friend request sent", "data": data}), 200

# Additional endpoint templates can be added here
@app.route('/friends', methods=['GET'])
def friends():
    # Retrieve list of friends (placeholder logic)
    friends_list = ["Alice", "Bob", "Charlie"]
    return jsonify({"friends": friends_list}), 200

if __name__ == '__main__':
    app.run(debug=True)