import requests
import json


LEETCODE_ENDPOINT_URL = "https://leetcode.com/graphql/"

HEADERS = {
    "Content-Type": "application/json"
}

# Define the merged query as a multiline string
QUERY = """
query friendData(
  $username: String!, 
  $userSlug: String!, 
  $year: Int, 
  $limit: Int!
) {
  userPublicProfile: matchedUser(username: $username) {
    profile {
      ranking
      userAvatar
      realName
    }
  }
  userProfileUserQuestionProgressV2: userProfileUserQuestionProgressV2(userSlug: $userSlug) {
    numAcceptedQuestions {
      count
      difficulty
    }
    numFailedQuestions {
      count
      difficulty
    }
    numUntouchedQuestions {
      count
      difficulty
    }
    userSessionBeatsPercentage {
      difficulty
      percentage
    }
    totalQuestionBeatsPercentage
  }
  allQuestionsCount {
    difficulty
    count
  }
  userSessionStats: matchedUser(username: $username) {
    submitStats {
      acSubmissionNum {
        difficulty
        count
        submissions
      }
      totalSubmissionNum {
        difficulty
        count
        submissions
      }
    }
  }
  userProfileCalendar: matchedUser(username: $username) {
    userCalendar(year: $year) {
      activeYears
      streak
      totalActiveDays
      submissionCalendar
    }
  }
  recentAcSubmissions: recentAcSubmissionList(username: $username, limit: $limit) {
    title
    titleSlug
    timestamp
  }
}
"""
def fetch_leetcode_friend_data(friend_username):
    variables = {
        "username": friend_username,
        "userSlug": friend_username,
        "year": 2025,
        "limit": 5
    }

    payload = {
        "query": QUERY,
        "variables": variables,
        "operationName": "friendData"
    }

    response = requests.post(LEETCODE_ENDPOINT_URL, headers=HEADERS, json=payload)

    return response.json()
