from flask import Flask, render_template, jsonify, request
from supabase import create_client, Client
import os
import requests
from dotenv import load_dotenv
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
from collections import OrderedDict
import json

from leetcode_endpoint import fetch_leetcode_user_data

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://leetcode.com"])

MAX_CONCURRENT_WORKERS = 12

CACHE_TTL = int(os.environ.get("CACHE_TTL", 300))
MAX_CACHE_SIZE = int(os.environ.get("MAX_CACHE_SIZE", 2000))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

class RedisCache:
    def __init__(self, redis_url=REDIS_URL, ttl=CACHE_TTL):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl
        self.cache_prefix = "leetcode:"
    
    def get(self, key):
        try:
            data = self.redis_client.get(self.cache_prefix + key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, key, value):
        try:
            self.redis_client.setex(
                self.cache_prefix + key,
                self.ttl,
                json.dumps(value)
            )
        except Exception as e:
            print(f"Redis set error: {e}")
    
    def size(self):
        try:
            return len(self.redis_client.keys(self.cache_prefix + "*"))
        except Exception:
            return 0
    
    def clear_expired(self):
        return 0

class LRUCache:
    def __init__(self, max_size=MAX_CACHE_SIZE, ttl=CACHE_TTL):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key):
        if key not in self.cache:
            return None
        
        data, timestamp = self.cache[key]
        
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        self.cache.move_to_end(key)
        return data
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)
        
        self.cache[key] = (value, time.time())
        self.cache.move_to_end(key)
    
    def size(self):
        return len(self.cache)
    
    def clear_expired(self):
        now = time.time()
        expired_keys = [
            key for key, (data, timestamp) in self.cache.items()
            if now - timestamp > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)

if REDIS_AVAILABLE:
    try:
        leetcode_cache = RedisCache()
        leetcode_cache.redis_client.ping()
        CACHE_TYPE = "redis"
        print("✓ Using Redis cache (shared across workers)")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("→ Falling back to in-memory cache (per-worker)")
        leetcode_cache = LRUCache()
        CACHE_TYPE = "memory"
else:
    leetcode_cache = LRUCache()
    CACHE_TYPE = "memory"
    print("→ Using in-memory cache (per-worker)")

def fetch_leetcode_user_data_cached(username):
    cached_data = leetcode_cache.get(username)
    if cached_data is not None:
        return cached_data
    
    data = fetch_leetcode_user_data(username)
    
    leetcode_cache.set(username, data)
    
    return data

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to LeetCode Friends!"}), 200

@app.route('/cache-stats', methods=['GET'])
def cache_stats():
    expired_count = leetcode_cache.clear_expired()
    return jsonify({
        "cache_type": CACHE_TYPE,
        "cache_size": leetcode_cache.size(),
        "max_cache_size": MAX_CACHE_SIZE if CACHE_TYPE == "memory" else "unlimited",
        "cache_ttl_seconds": CACHE_TTL,
        "expired_entries_cleared": expired_count,
        "memory_usage_estimate_mb": round(leetcode_cache.size() * 0.02, 2),
        "shared_across_workers": CACHE_TYPE == "redis"
    }), 200

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/user-is-registered', methods=['GET'])
def user_is_registered():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error checking user registration: {str(e)}"}), 500

    is_registered = bool(user_response.data)
    return jsonify({"is_registered": is_registered}), 200

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400
    
    leetcode_url = f"https://leetcode.com/u/{username}"
    leetcode_response = requests.get(leetcode_url)
    if leetcode_response.status_code == 404:
        return jsonify({"error": f"LeetCode user '{username}' not found"}), 404

    try:
        existing_user = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error checking existing user: {str(e)}"}), 500

    if existing_user.data:
        return jsonify({"error": "User already exists"}), 400

    try:
        response = supabase.table("users").insert({"username": username}).execute()
    except Exception as e:
        return jsonify({"error": f"Error registering user: {str(e)}"}), 500

    return jsonify({"message": f"User {username} registered!", "user": response.data}), 200

@app.route('/friend-request/send', methods=['POST'])
def send_friend_request():
    data = request.get_json()
    sender_username = data.get("sender_username")
    receiver_username = data.get("receiver_username")

    leetcode_url = f"https://leetcode.com/u/{receiver_username}"
    leetcode_response = requests.get(leetcode_url)
    if leetcode_response.status_code == 404:
        return jsonify({"error": f"LeetCode user '{receiver_username}' not found"}), 404
    
    try:
        sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching sender: {str(e)}"}), 500
    
    try:
        receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching receiver: {str(e)}"}), 500
    
    if not sender_response.data:
        return jsonify({"error": "Invalid sender"}), 404

    if not receiver_response.data:
        return jsonify({"error": f"{receiver_username} is not registered in LeetCode Friends!"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]

    try:
        friendship_response = supabase.table("friendships") \
            .select("id") \
            .eq("user_id", sender_id) \
            .eq("friend_id", receiver_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error checking friendship: {str(e)}"}), 500

    if friendship_response.data:
        return jsonify({"error": "These users are already friends"}), 400
    
    try:
        response = supabase.table("pending_friend_requests").insert({
            "sender_id": sender_id,
            "receiver_id": receiver_id
        }).execute()
    except Exception as e:
        return jsonify({"error": f"Error sending friend request: {str(e)}"}), 500
    
    return jsonify({"message": "Friend request sent!", "response": response.data}), 200

@app.route('/friend-request/accept', methods=['POST'])
def accept_friend_request():
    data = request.get_json()
    sender_username = data.get("sender_username")
    receiver_username = data.get("receiver_username")
    
    try:
        sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching sender: {str(e)}"}), 500
    
    try:
        receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching receiver: {str(e)}"}), 500
    
    if not sender_response.data or not receiver_response.data:
        return jsonify({"error": "Sender or receiver not found"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]
    
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
    
    try:
        supabase.table("pending_friend_requests") \
            .delete() \
            .eq("sender_id", sender_id) \
            .eq("receiver_id", receiver_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error deleting pending friend request: {str(e)}"}), 500
    
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

@app.route('/friend-request/decline', methods=['POST'])
def decline_friend_request():
    data = request.get_json()
    sender_username = data.get("sender_username")
    receiver_username = data.get("receiver_username")
    
    try:
        sender_response = supabase.table("users").select("id").eq("username", sender_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching sender: {str(e)}"}), 500
    
    try:
        receiver_response = supabase.table("users").select("id").eq("username", receiver_username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching receiver: {str(e)}"}), 500
    
    if not sender_response.data or not receiver_response.data:
        return jsonify({"error": "Sender or receiver not found"}), 404
    
    sender_id = sender_response.data[0]["id"]
    receiver_id = receiver_response.data[0]["id"]
    
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

@app.route('/friend-request/incoming', methods=['GET'])
def get_incoming_friend_requests():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching user: {str(e)}"}), 500

    if not user_response.data:
        return jsonify({"error": "User not found"}), 404

    user_id = user_response.data[0]["id"]

    try:
        pending_response = supabase.table("pending_friend_requests") \
            .select("sender_id, created_at, sender_username:users!pending_friend_requests_sender_id_fkey(username)") \
            .eq("receiver_id", user_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching incoming friend requests: {str(e)}"}), 500

    for friend_request in pending_response.data:
        if isinstance(friend_request.get('sender_username'), dict):
            friend_request['sender_username'] = friend_request['sender_username'].get('username')

    return jsonify({"incoming_friend_requests": pending_response.data}), 200

@app.route('/friend-request/outgoing', methods=['GET'])
def get_outgoing_friend_requests():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching user: {str(e)}"}), 500

    if not user_response.data:
        return jsonify({"error": "User not found"}), 404

    user_id = user_response.data[0]["id"]

    try:
        pending_response = supabase.table("pending_friend_requests") \
            .select("receiver_id, created_at, receiver_username:users!pending_friend_requests_receiver_id_fkey(username)") \
            .eq("sender_id", user_id) \
            .execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching outgoing friend requests: {str(e)}"}), 500

    for friend_request in pending_response.data:
        if isinstance(friend_request.get('receiver_username'), dict):
            friend_request['receiver_username'] = friend_request['receiver_username'].get('username')

    return jsonify({"outgoing_friend_requests": pending_response.data}), 200

@app.route('/friends', methods=['GET'])
def get_friends():
    username = request.args.get("username")
    fresh = request.args.get("fresh", "false").lower() == "true"
    
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    try:
        user_response = supabase.table("users").select("id").eq("username", username).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching user: {str(e)}"}), 500

    if not user_response.data:
        return jsonify({"error": "User not found"}), 404

    user_id = user_response.data[0]["id"]

    try:
        friends_response = supabase.table("friendships").select("friend_id, friend_username:users!friendships_friend_id_fkey(username)").eq("user_id", user_id).execute()
    except Exception as e:
        return jsonify({"error": f"Error fetching friends: {str(e)}"}), 500
    
    def fetch_friend_data(friend):
        friend_username = friend.get("friend_username")
        if friend_username:
            if isinstance(friend.get('friend_username'), dict):
                friend['friend_username'] = friend_username.get('username')
            try:
                if fresh:
                    leetcode_data = fetch_leetcode_user_data(friend['friend_username'])
                else:
                    leetcode_data = fetch_leetcode_user_data_cached(friend['friend_username'])
                friend["data"] = leetcode_data.get("data")
            except Exception as e:
                friend["data"] = {"error": str(e)}
        return friend
    
    friends_data = friends_response.data
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
        future_to_friend = {executor.submit(fetch_friend_data, friend): friend for friend in friends_data}
        
        completed_friends = []
        for future in as_completed(future_to_friend):
            try:
                completed_friends.append(future.result())
            except Exception as e:
                friend = future_to_friend[future]
                friend["data"] = {"error": str(e)}
                completed_friends.append(friend)
    
    return jsonify({"friends": completed_friends}), 200

@app.route('/current-user-info/', methods=['GET'])
def get_leetcode_user_data():
    username = request.args.get("username")
    fresh = request.args.get("fresh", "false").lower() == "true"
    
    if not username:
        return jsonify({"error": "username parameter is required"}), 400
    try:
        if fresh:
            user_data = fetch_leetcode_user_data(username)
        else:
            user_data = fetch_leetcode_user_data_cached(username)
        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({"error": f"Error fetching data for {username}: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)