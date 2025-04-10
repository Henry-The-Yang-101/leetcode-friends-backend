import requests

LEETCODE_ENDPOINT_URL = "https://leetcode.com/graphql/"

HEADERS = {
    "Content-Type": "application/json"
}

# Read the contents of the file draft_payload.gql
with open("draft_payload.gql", "r") as gql_file:
    QUERY = gql_file.read()

def fetch_leetcode_user_data(username):
    variables = {
        "username": username,
        "userSlug": username,
        "year": 2025,
        "limit": 20
    }

    payload = {
        "query": QUERY,
        "variables": variables,
        "operationName": "userData"
    }

    response = requests.post(LEETCODE_ENDPOINT_URL, headers=HEADERS, json=payload)

    return response.json()
