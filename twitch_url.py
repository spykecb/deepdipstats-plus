import requests
from datetime import datetime, timedelta
import pytz
import json
import os
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

class TwitchUrl:
    __oauth_token = None
    user_videos_cache = None

    def init(self) -> None:
        self.__oauth_token = self.get_oauth_token()
        if self.__oauth_token is None:
            self.refresh_oath_token()
        self.user_videos_cache = dict()

    def get_oauth_token(self):
        if not os.path.isfile('oauth_token.json'):
            return None

        with open('oauth_token.json', 'r') as json_file:
            data = ''.join(json_file.readlines())
            if not data:
                return None
            loaded_json = json.loads(data)
            return loaded_json["access_token"]

    def refresh_oath_token(self):
        if CLIENT_ID == None or CLIENT_ID == "" or CLIENT_SECRET == None or CLIENT_SECRET == "":
            print("Please set twitch client ID and secret in the .env file!")
            return
        # URL for the token request
        url = 'https://id.twitch.tv/oauth2/token'

        # Headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # Data
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }

        # Send POST request
        print("Calling Twitch API... (refresh)")
        response = requests.post(url, headers=headers, data=data)
        json_file = response.json()
        with open('oauth_token.json', 'w') as file:
            json.dump(json_file, file, indent=4)

        print("Token saved to 'twitch_token.json'")
        self.__oauth_token = json_file["access_token"]

    # Helper function to get the video ID and the start time
    def get_video_info(self, streamer_name, timestamp_utc):
        if CLIENT_ID == None or CLIENT_ID == "" or CLIENT_SECRET == None or CLIENT_SECRET == "":
            print("Please set twitch client ID and secret in the .env file!")
            return
        if streamer_name not in self.user_videos_cache:
            print("Calling Twitch API...")
            headers = {
                'Client-ID': CLIENT_ID,
                'Authorization': f'Bearer {self.__oauth_token}'
            }

            # Get user ID
            user_url = f'https://api.twitch.tv/helix/users?login={streamer_name}'
            user_response = requests.get(user_url, headers=headers).json()
            user_id = user_response['data'][0]['id']

            # Get videos
            videos_url = f'https://api.twitch.tv/helix/videos?user_id={user_id}'
            videos_response = requests.get(videos_url, headers=headers).json()
            self.user_videos_cache[streamer_name] = videos_response['data']

        for video in self.user_videos_cache[streamer_name]:
            start_time = video['created_at']
            start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
            duration_str = video['duration']
            try:
                hours = int(duration_str.split('h')[0]) if 'h' in duration_str else 0
                hours_rem = duration_str.split('h')[1] if 'h' in duration_str else duration_str
                minutes = int(hours_rem.split('m')[0]) if 'm' in duration_str else 0
                minutes_rem = hours_rem.split('m')[1] if 'm' in hours_rem else hours_rem
                seconds = int(minutes_rem[:-1]) if 's' in minutes_rem else 0
                end_datetime = start_datetime + timedelta(hours=hours, minutes=minutes, seconds=seconds)

                # Check if the timestamp falls within the video duration
                timestamp_datetime = datetime.strptime(timestamp_utc, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
                if start_datetime <= timestamp_datetime <= end_datetime:
                    return video['id'], start_datetime
            except:
                print(f"Failed to parse {duration_str}")
                return None, None

        return None, None
    
    def get_video_url(self, streamer_name, timestamp_utc):
        # Get video info
        video_id, start_datetime = self.get_video_info(streamer_name, self._convert_datetime(timestamp_utc))

        if video_id:
            # Calculate the offset
            timestamp_datetime = datetime.strptime(self._convert_datetime(timestamp_utc), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
            offset = timestamp_datetime - start_datetime
            hours, remainder = divmod(offset.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)

            # Construct the URL
            timestamp_str = f'{int(hours)}h{int(minutes)}m{int(seconds)}s'
            url = f'https://www.twitch.tv/videos/{video_id}?t={timestamp_str}'
            return url
        else:
            return None

    def _convert_datetime(self, datetime_str):
        year = datetime.now().year
        # Parse the input datetime string
        datetime_obj = datetime.strptime(datetime_str, "%m/%d, %I:%M %p")
        
        # Set the year
        datetime_obj = datetime_obj.replace(year=year)
        
        # Convert to ISO 8601 format with UTC timezone
        datetime_iso = datetime_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return datetime_iso

