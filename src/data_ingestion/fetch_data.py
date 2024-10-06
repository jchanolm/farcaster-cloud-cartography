import os
import time
import json
import boto3 
from dotenv import load_dotenv
import requests as r
from requests import RequestException
from botocore.exceptions import NoCredentialsError, ClientError
import logging
from datetime import datetime, timezone

load_dotenv()

class DataFetcher:
    def __init__(self, data_dir="data/raw", max_age_seconds=86400):
        self.data_dir = data_dir
        self.max_age_seconds = max_age_seconds
        self.NEYNAR_API_KEY = os.getenv('NEYNAR_API_KEY')
        self.bucket_name = 'cloud-cartography'
        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY
        )
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Farcaster Epoch (Jan 1, 2021 00:00:00 UTC)
        self.FARCASTER_EPOCH = datetime(2021, 1, 1, tzinfo=timezone.utc)

    def convert_timestamp(self, timestamp):
        """Convert Farcaster timestamp to UTC datetime."""
        return self.FARCASTER_EPOCH + timedelta(seconds=int(timestamp))

    def check_s3_exists(self, fid: str) -> bool:
        s3_key = f'user_{fid}_data.json'
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                self.logger.error(f"Error checking existence of {s3_key} in S3: {e}")
                return False

    def load_data_from_s3(self, fid: str):
        s3_key = f'user_{fid}_data.json'
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            self.logger.error(f"Error loading data from S3 for FID {fid}: {e}")
            return None

    def upload_json_to_s3(self, data, fid: str):
        s3_key = f'user_{fid}_data.json'
        try:
            json_data = json.dumps(data)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json',
                ACL='public-read'
            )
            self.logger.info(f"Successfully uploaded {s3_key} to {self.bucket_name}")
            return True
        except (NoCredentialsError, ClientError) as e:
            self.logger.error(f"Failed to upload {s3_key} to {self.bucket_name}. Error: {e}")
            return False

    def query_neynar_hub(self, endpoint, params=None):
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

        while True:
            for attempt in range(max_retries):
                try:
                    time.sleep(0.1)
                    response = r.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'messages' in data:
                        for message in data['messages']:
                            if 'timestamp' in message.get('data', {}):
                                message['data']['timestamp'] = self.convert_timestamp(message['data']['timestamp']).isoformat()
                        all_messages.extend(data['messages'])
                        self.logger.info(f"Retrieved {len(all_messages)} messages total...")
                    
                    if 'nextPageToken' in data and data['nextPageToken']:
                        params['pageToken'] = data['nextPageToken']
                        break
                    else:
                        return all_messages
                    
                except RequestException as e:
                    if attempt == max_retries - 1:
                        self.logger.error(f"Failed after {max_retries} attempts. Error: {e}")
                        return all_messages
                    else:
                        self.logger.warning(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2

    def query_neynar_api_for_users(self, fids):
        base_url = "https://api.neynar.com/v2/farcaster/user/bulk"
        headers = {
            "accept": "application/json",
            "api_key": self.NEYNAR_API_KEY
        }
        params = {
            "fids": ",".join(map(str, fids))
        }

        try:
            time.sleep(0.1)
            response = r.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if 'users' not in data:
                self.logger.warning(f"Unexpected response format. Response: {data}")
            return data
        except RequestException as e:
            self.logger.error(f"Error querying Neynar API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status code: {e.response.status_code}")
                self.logger.error(f"Response content: {e.response.content}")
            return None

    def get_user_metadata(self, fid):
        endpoint = "userDataByFid"
        params = {'fid': fid, 'USER_DATA_TYPE': 'USER_DATA_TYPE_DISPLAY'}
        messages = self.query_neynar_hub(endpoint=endpoint, params=params)
        
        user_data = {
            'bio': None,
            'username': None,
            'fid': str(fid)
        }

        for message in messages:
            if 'data' in message and 'userDataBody' in message['data']:
                user_data_body = message['data']['userDataBody']
                if user_data_body['type'] == 'USER_DATA_TYPE_BIO':
                    user_data['bio'] = user_data_body['value']
                elif user_data_body['type'] == 'USER_DATA_TYPE_USERNAME':
                    user_data['username'] = user_data_body['value']
            
            if user_data['bio'] and user_data['username']:
                break

        return user_data

    def get_user_follows(self, fid):
        endpoint = "linksByFid"
        params = {
            'fid': str(fid), 
            'link_type': 'follow'
        }
        messages = self.query_neynar_hub(endpoint=endpoint, params=params)

        return [{
            'source': str(fid),
            'target': str(item['data']['linkBody'].get('targetFid')),
            'timestamp': item['data'].get('timestamp'),
            'edge_type': 'FOLLOWS'
        } for item in messages 
          if "data" in item 
          and "linkBody" in item["data"] 
          and item['data']['linkBody'].get('targetFid') 
          and item['data'].get('timestamp')]

    def get_user_likes(self, fid):
        endpoint = "reactionsByFid"
        params = {
            'fid': fid,
            'reaction_type': 'REACTION_TYPE_LIKE'
        }
        messages = self.query_neynar_hub(endpoint, params)

        return [{
            'source': str(fid),
            'target': str(item['data']['reactionBody']['targetCastId'].get('fid')),
            'target_hash': item['data']['reactionBody']['targetCastId'].get('hash'),
            'timestamp': item['data'].get('timestamp'),
            'edge_type': 'LIKED'
        } for item in messages 
          if "data" in item 
          and "reactionBody" in item["data"] 
          and item['data']['reactionBody'].get('targetCastId') 
          and item['data'].get('timestamp')]

    def get_user_recasts(self, fid):
        endpoint = "reactionsByFid"
        params = {
            'fid': fid,
            'reaction_type': 'REACTION_TYPE_RECAST'
        }
        messages = self.query_neynar_hub(endpoint, params)

        return [{
            'source': str(fid),
            'target': str(item['data']['reactionBody']['targetCastId'].get('fid')),
            'target_hash': item['data']['reactionBody']['targetCastId'].get('hash'),
            'timestamp': item['data'].get('timestamp'),
            'edge_type': 'RECASTED'
        } for item in messages 
          if "data" in item 
          and "reactionBody" in item["data"] 
          and item['data']['reactionBody'].get('targetCastId') 
          and item['data'].get('timestamp')]

    def get_user_casts(self, fid):
        self.logger.info(f"Collecting casts for user {fid}.....")
        endpoint = "castsByFid"
        params = {'fid': fid}
        messages = self.query_neynar_hub(endpoint=endpoint, params=params)

        cast_data_list = [{
            'source': str(fid),
            'target': str(message['data']['castAddBody']['parentCastId']['fid']),
            'timestamp': message['data']['timestamp'],
            'edge_type': 'REPLIED'
        } for message in messages 
          if 'data' in message 
          and 'castAddBody' in message['data'] 
          and message['data']['castAddBody'].get('parentCastId')]

        self.logger.info(f"Retrieved {len(cast_data_list)} replies for user: {fid}...")
        return cast_data_list

    def get_user_data(self, fid):
        return {
            'core_node_metadata': self.get_user_metadata(fid),
            'likes': self.get_user_likes(fid),
            'recasts': self.get_user_recasts(fid),
            'casts': self.get_user_casts(fid),
            'following': self.get_user_follows(fid)
        }

    def collect_connections_ids(self, user_object):
        unique_fids = set()
        
        if 'core_node_metadata' in user_object and 'fid' in user_object['core_node_metadata']:
            unique_fids.add(user_object['core_node_metadata']['fid'])
        
        for key in ['following', 'likes', 'recasts', 'casts']:
            if key in user_object:
                unique_fids.update(item['target'] for item in user_object[key] if 'target' in item)
                unique_fids.update(item['source'] for item in user_object[key] if 'source' in item)

        return unique_fids

    def get_user_metadata_for_connections(self, user_object):
        all_fids = list(self.collect_connections_ids(user_object))
        user_metadata_list = []

        for i in range(0, len(all_fids), 100):
            batch = all_fids[i:i+100]
            response = self.query_neynar_api_for_users(batch)
            
            if response and 'users' in response:
                user_metadata_list.extend([{
                    'fid': str(user['fid']),
                    'username': user.get('username'),
                    'display_name': user.get('display_name'),
                    'pfp_url': user.get('pfp_url'),
                    'follower_count': user.get('follower_count'),
                    'following_count': user.get('following_count')
                } for user in response['users']])

        return user_metadata_list

    def get_all_users_data(self, fids):
        all_user_data = {}
        for fid in fids:
            self.logger.info(f"Processing FID: {fid}")
            if self.check_s3_exists(fid):
                self.logger.info(f"Data for FID {fid} exists in S3. Loading from S3.")
                user_data = self.load_data_from_s3(fid)
            else:
                self.logger.info(f"Data for FID {fid} not found in S3. Fetching from API.")
                user_data = self.get_user_data(fid)
                if user_data:
                    self.logger.info(f"Collecting connections metadata for FID: {fid}")
                    connections_metadata = self.get_user_metadata_for_connections(user_data)
                    user_data['connections_metadata'] = connections_metadata
                    self.upload_json_to_s3(user_data, fid)

            if user_data:
                all_user_data[fid] = user_data
            else:
                self.logger.warning(f"Failed to retrieve data for FID {fid}")

        return all_user_data

    def get_all_users_data_s3(self, fids):
        """
        Fetches and stores data for multiple users in S3.
        Processes each fid individually by fetching user data and collecting connections metadata.
        Uploads to S3 only after adding connections metadata.

        Args:
            fids (List[str]): List of user IDs (FIDs) as strings.
        """
        total_users = len(fids)
        processed_users = 0

        for fid in fids:
            try:
                print(f"Processing FID: {fid} ({processed_users + 1}/{total_users})")

                # Fetch user data
                user_data = self.get_user_data(fid)
                if not user_data:
                    print(f"No data fetched for FID {fid}. Skipping.")
                    continue

                # Collect connections metadata
                print(f"Collecting connections metadata for FID: {fid}")
                connections_metadata = self.get_user_metadata_for_connections(user_data)

                # Add connections metadata to user data
                user_data['connections_metadata'] = connections_metadata
                print(f"Added connections metadata to user data for FID: {fid}")

                # Upload user data to S3
                s3_key = f'user_{fid}_data.json'
                upload_success = self.upload_json_to_s3(user_data, s3_key)
                if upload_success:
                    print(f"Successfully uploaded data for FID: {fid} to S3.")
                else:
                    print(f"Failed to upload data for FID: {fid} to S3.")

                processed_users += 1

            except Exception as e:
                print(f"An error occurred while processing FID {fid}: {str(e)}")
                continue

            print(f"Completed processing for FID: {fid}\n")

        print(f"Finished processing {processed_users} out of {total_users} users.")
        if processed_users < total_users:
            print(f"Warning: {total_users - processed_users} users were not processed successfully.")        

if __name__ == "__main__":
    fetcher = DataFetcher()
    test_fids = ['190000', '190001']
    result = fetcher.get_all_users_data(test_fids)
    print(f"Processed data for {len(result)} users.")