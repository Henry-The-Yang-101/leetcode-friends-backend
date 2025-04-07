from flask import Flask, render_template, jsonify, request
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Retrieve Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Endpoint for sending a friend request
@app.route('/friend_request/send', methods=['POST'])
def send_friend_request():
    data = request.get_json()
    sender_username = data.get("sender_username")
    receiver_username = data.get("receiver_username")
    
    # Query the users table for sender and receiver by username
    sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    
    # Check if both users were found
    if not sender_response.data or not receiver_response.data:
        return jsonify({"error": "Sender or receiver not found"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]
    
    # Insert the friend request into the "pending_friend_requests" table
    response = supabase.table("pending_friend_requests").insert({
        "sender_id": sender_id,
        "receiver_id": receiver_id
    }).execute()
    
    return jsonify({"message": "Friend request sent", "response": response.data}), 200

# Endpoint for sending a friend request
@app.route('/friend_request/accept', methods=['POST'])
def accept_friend_request():
    
    
    return jsonify({"message": "Friend request sent", "response": response.data}), 200

# Endpoint for declining an friend request
@app.route('/friend_request/decline', methods=['POST'])
def decline_friend_request():
    
    return jsonify({"message": "Friend request sent", "response": response.data}), 200

# Endpoint to retrieve friends (this is placeholder logic)
@app.route('/friends', methods=['GET'])
def get_friends():
    # Example: Query the "friendships" table (update as needed)
    response = supabase.table("friendships").select("*").execute()
    return jsonify({"friends": response.data}), 200

# Endpoint to retrieve friends (this is placeholder logic)
@app.route('/friend_request/list', methods=['GET'])
def get_incoming_friend_requests():
    # Example: Query the "friendships" table (update as needed)
    response = supabase.table("friendships").select("*").execute()
    return jsonify({"friends": response.data}), 200

if __name__ == '__main__':
    app.run(debug=True)