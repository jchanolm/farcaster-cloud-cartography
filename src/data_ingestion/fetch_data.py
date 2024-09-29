import os
import time 
import json 
from dotenv import load_dotenv
import requests as r 
from requests import RequestException

load_dotenv()

class DataFetcher: 
    def __init__(self, data_dir="data/raw", max_age_seconds=86400):
        """
        Initializes DataFetcher instance.
        - data_dir (str): Directory where data is stored
        - max_age_seconds (int): Maximum age of cached data in seconds (default: 24 hours)
        """
        self.data_dir = data_dir 
        self.max_age_seconds = max_age_seconds
        self.NEYNAR_API_KEY = os.getenv('NEYNAR_API_KEY')

        os.makedirs(self.data_dir, exist_ok=True)

    def query_neynar_api(self, endpoint, params=None):
        """
        Queries the Neynar API with pagination support.
        """
        base_url = "https://hub-api.neynar.com/v1/"
        headers = {
            "Content-Type": "application/json",
            "api_key": self.NEYNAR_API_KEY,
        }
        url = f"{base_url}{endpoint}"
        params = params or {}
        params['pageSize'] = 1000

        all_messages = []
        max_retries = 3
        retry_delay = 1
        successful_calls = 0

        while True:
            for attempt in range(max_retries):
                try:
                    response = r.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'messages' in data:
                        successful_calls += 1
                        print(f"Successful call number: {successful_calls}")
                        print(f"New messages retrieved: {len(data['messages'])}...")
                        all_messages.extend(data['messages'])
                        print(f"Retrieved {len(all_messages)} messages total...")
                    
                    if 'nextPageToken' in data and data['nextPageToken']:
                        params['pageToken'] = data['nextPageToken']
                        break  # Successful, move to next page
                    else:
                        return all_messages  # No more pages, return all messages
                    
                except RequestException as e:
                    if attempt == max_retries - 1:
                        print(f"Failed after {max_retries} attempts. Error: {e}")
                        return all_messages  # Return whatever messages we've collected so far
                    else:
                        print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff

    def is_data_stale(self, fid):
        """
        Checks if data for the given FID is missing or stale.
        """
        filepath = os.path.join(self.data_dir, f'user_{fid}.json')
        if not os.path.exists(filepath):
            return True 
        file_mod_time = os.path.getmtime(filepath)
        return (time.time() - file_mod_time) > self.max_age_seconds

    def get_user_metadata(self, fid):
        """Fetches user metadata for a single FID."""
        endpoint = "userDataByFid"
        params = {'fid': fid, 'USER_DATA_TYPE': 'USER_DATA_TYPE_DISPLAY'}
        messages = self.query_neynar_api(endpoint=endpoint, params=params)
        
        user_data = {
            'bio': None,
            'username': None,
            'fid': fid
        }

        for message in messages:
            if 'data' in message and 'userDataBody' in message['data']:
                user_data_body = message['data']['userDataBody']
                if user_data_body['type'] == 'USER_DATA_TYPE_BIO':
                    user_data['bio'] = user_data_body['value']
                elif user_data_body['type'] == 'USER_DATA_TYPE_USERNAME':
                    user_data['username'] = user_data_body['value']
            
            if user_data['bio'] and user_data['username']:
                break  # Exit loop if we've found both bio and username

        return user_data
    
    def get_user_follows(self, fid):
        """Fetches users followed by provided Farcaster ID"""
        endpoint = "linksByFid"
        params = {
            'fid': fid, 
            'link_type': 'follow'
        }
        messages = self.query_neynar_api(endpoint=endpoint, params=params)

        extracted_following = []
        for item in messages:
            if "data" in item and "linkBody" in item["data"]:
                target_fid = item['data']['linkBody'].get('targetFid')
                timestamp = item['data'].get('timestamp')
                if target_fid and timestamp:
                    extracted_following.append({
                        'target_fid': target_fid,
                        'timestamp': timestamp
                    })
        return extracted_following
    
    def get_user_followers(self, fid):
        """Fetches followers for provided Farcaster ID"""
        endpoint = "linksByTargetFid"
        params = {
            'link_type': 'follow', 
            'target_fid': fid
        }
        messages = self.query_neynar_api(endpoint, params)

        extracted_followers = []
        for item in messages:
            if "data" in item and "linkBody" in item["data"]:
                follower_id = item['data']['linkBody'].get('fid')
                timestamp = item['data'].get('timestamp')
                if fid and timestamp:
                    extracted_followers.append({
                        'fid': follower_id,
                        'timestamp': timestamp 
                    })
        return extracted_followers
    
    def get_user_likes(self, fid):
        """Fetches likes for provided Farcaster ID"""
        endpoint = "reactionsByFid"
        params = {
            'fid': fid,
            'reaction_type': 'REACTION_TYPE_LIKE'
        }
        messages = self.query_neynar_api(endpoint, params)

        extracted_likes = []
        for item in messages:
            if "data" in item and "reactionBody" in item["data"]:
                target_cast = item['data']['reactionBody'].get('targetCastId')
                timestamp = item['data'].get('timestamp')
                if target_cast and timestamp:
                    extracted_likes.append({
                        'target_fid': target_cast.get('fid'),
                        'target_hash': target_cast.get('hash'),
                        'timestamp': timestamp
                     })
        print(extracted_likes)
        return extracted_likes

    def get_user_recasts(self, fid):
        """Fetches recasts for provided Farcaster ID"""
        endpoint = "reactionsByFid"
        params = {
            'fid': fid,
            'reaction_type': 'REACTION_TYPE_RECAST'
        }
        messages = self.query_neynar_api(endpoint, params)

        extracted_recasts = []
        for item in messages:
            if "data" in item and "reactionBody" in item["data"]:
                target_cast = item['data']['reactionBody'].get('targetCastId')
                timestamp = item['data'].get('timestamp')
                if target_cast and timestamp:
                    extracted_recasts.append({
                        'target_fid': target_cast.get('fid'),
                        'target_hash': target_cast.get('hash'),
                        'timestamp': timestamp
                     })
        return extracted_recasts


    def get_user_data(self, fid):
        """Assembles all data for a single user."""
        return {
            'metadata': self.get_user_metadata(fid),
            'follows': self.get_user_follows(fid),
            'followers': self.get_user_followers(fid),
            'likes': self.get_user_likes(fid),
            'recasts': self.get_user_recasts(fid)
        }

    def get_all_users_data(self, fids):
        """Fetches and stores data for multiple users."""
        all_user_data = {}
        for fid in fids:
            user_data = self.get_user_data(fid)
            all_user_data[fid] = user_data

            filename = f'user_{fid}_data.json'
            with open(os.path.join(self.data_dir, filename), 'w') as f:
                json.dump(user_data, f)

        return all_user_data

            

if __name__ == "__main__":
    fetcher = DataFetcher()
    fetcher.get_all_users_data([190000])
    # user_data = fetcher.fetch_and_store_user_data([5, 1677])
    # follows = fetcher.get_user_follows([3])
    # followers = fetcher.get_user_followers([190000])
    # likes = fetcher.get_user_likes([190000])
    # recasts = fetcher.get_user_recasts([3])


