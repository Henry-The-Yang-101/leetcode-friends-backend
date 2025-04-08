from flask import Flask, render_template, jsonify, request
from supabase import create_client, Client
import os
from dotenv import load_dotenv

from leetcode_endpoint import fetch_leetcode_friend_data

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
    
    # Query the users table for sender by username
    try:
        sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching sender: {str(e)}"}), 500
    
    # Query the users table for receiver by username
    try:
        receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching receiver: {str(e)}"}), 500
    
    # Check if both users were found
    if not sender_response.data or not receiver_response.data:
        return jsonify({"error": "Sender or receiver not found"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]
    
    # Insert the friend request into the "pending_friend_requests" table
    try:
        response = supabase.table("pending_friend_requests").insert({
            "sender_id": sender_id,
            "receiver_id": receiver_id
        }).execute()
    except Exception as e:
        return jsonify({"error": f"Error sending friend request: {str(e)}"}), 500
    
    return jsonify({"message": "Friend request sent!", "response": response.data}), 200

@app.route('/friend_request/accept', methods=['POST'])
def accept_friend_request():
    data = request.get_json()
    sender_username = data.get("sender_username")
    receiver_username = data.get("receiver_username")
    
    # Query the users table for sender by username
    try:
        sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching sender: {str(e)}"}), 500
    
    # Query the users table for receiver by username
    try:
        receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching receiver: {str(e)}"}), 500
    
    # Check if both users were found
    if not sender_response.data or not receiver_response.data:
        return jsonify({"error": "Sender or receiver not found"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]
    
    # Check if the pending friend request exists
    try:
        pending_response = supabase.table("pending_friend_requests") \
            .select("*") \
            .eq("sender_id", sender_id) \
            .eq("receiver_id", receiver_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching pending friend request: {str(e)}"}), 500
    
    if not pending_response.data:
        return jsonify({"error": "Friend request not found"}), 404
    
    # Delete the pending friend request
    try:
        supabase.table("pending_friend_requests") \
            .delete() \
            .eq("sender_id", sender_id) \
            .eq("receiver_id", receiver_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error deleting pending friend request: {str(e)}"}), 500
    
    # Insert friendship relationships in both directions
    try:
        insert_response = supabase.table("friendships").insert([
            {"user_id": sender_id, "friend_id": receiver_id},
            {"user_id": receiver_id, "friend_id": sender_id}
        ]).execute()
    except Exception as e:
        return jsonify({"error": f"Error inserting friendships: {str(e)}"}), 500
    
    return jsonify({
        "message": f"Accepted {sender_username}'s friend request!",
        "friendship": insert_response.data
    }), 200

# Endpoint for declining a friend request
@app.route('/friend_request/decline', methods=['POST'])
def decline_friend_request():
    data = request.get_json()
    sender_username = data.get("sender_username")
    receiver_username = data.get("receiver_username")
    
    # Query the users table for sender by username
    try:
        sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching sender: {str(e)}"}), 500
    
    # Query the users table for receiver by username
    try:
        receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching receiver: {str(e)}"}), 500
    
    # Check if both users were found
    if not sender_response.data or not receiver_response.data:
        return jsonify({"error": "Sender or receiver not found"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]
    
    # Check if the pending friend request exists
    try:
        pending_response = supabase.table("pending_friend_requests") \
            .select("*") \
            .eq("sender_id", sender_id) \
            .eq("receiver_id", receiver_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching pending friend request: {str(e)}"}), 500
    
    if not pending_response.data:
        return jsonify({"error": "Friend request not found"}), 404
    
    # Delete the pending friend request
    try:
        supabase.table("pending_friend_requests") \
            .delete() \
            .eq("sender_id", sender_id) \
            .eq("receiver_id", receiver_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error deleting friend request: {str(e)}"}), 500
    
    return jsonify({
        "message": f"Declined {sender_username}'s friend request."
    }), 200

# Endpoint to retrieve incoming friend requests for a specific user
@app.route('/friend_request/incoming', methods=['GET'])
def get_incoming_friend_requests():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    # Query the users table to get the user ID for the provided username
    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching user: {str(e)}"}), 500

    if not user_response.data:
        return jsonify({"error": "User not found"}), 404

    user_id = user_response.data[0]["id"]

    # Query pending_friend_requests where the user is the receiver
    try:
        pending_response = supabase.table("pending_friend_requests") \
            .select("*") \
            .eq("receiver_id", user_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching incoming friend requests: {str(e)}"}), 500

    return jsonify({"incoming_friend_requests": pending_response.data}), 200

# Endpoint to retrieve outgoing friend requests for a specific user
@app.route('/friend_request/outgoing', methods=['GET'])
def get_outgoing_friend_requests():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    # Query the users table to get the user ID for the provided username
    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching user: {str(e)}"}), 500

    if not user_response.data:
        return jsonify({"error": "User not found"}), 404

    user_id = user_response.data[0]["id"]

    # Query pending_friend_requests where the user is the sender
    try:
        pending_response = supabase.table("pending_friend_requests") \
            .select("*") \
            .eq("sender_id", user_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching outgoing friend requests: {str(e)}"}), 500

    return jsonify({"outgoing_friend_requests": pending_response.data}), 200

# Endpoint to retrieve friends
@app.route('/friends', methods=['GET'])
def get_friends():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    # Query the users table for the provided username
    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching user: {str(e)}"}), 500

    if not user_response.data:
        return jsonify({"error": "User not found"}), 404

    user_id = user_response.data[0]["id"]

    # Query the friendships table for rows where user_id matches the retrieved user ID
    try:
        friends_response = supabase.table("friendships").select("friend_id, friend:users(username)").eq("user_id", user_id).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching friends: {str(e)}"}), 500
    
    return jsonify({"friends": friends_response.data}), 200

@app.route('/temp', methods=['GET'])
def temp():
    # Example usage of the fetch_leetcode_friend_data function
    friend_username = "SavageSparky101"
    friend_data = fetch_leetcode_friend_data(friend_username)
    return jsonify(friend_data), 200

if __name__ == '__main__':
    app.run(debug=True)