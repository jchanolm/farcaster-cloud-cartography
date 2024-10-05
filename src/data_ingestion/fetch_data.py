import os
import time
import json
import boto3 
from dotenv import load_dotenv
import requests as r
from requests import RequestException
from botocore.exceptions import NoCredentialsError, ClientError


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
        self.bucket_name = 'cloud-cartography'
        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        os.makedirs(self.data_dir, exist_ok=True)

    def check_s3_exists(self, s3_key: str) -> bool:
        """
        Checks if a specific S3 object exists.
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                self.logger.error(f"Error checking existence of {s3_key} in S3: {e}")
                return False

    def query_neynar_hub(self, endpoint, params=None):
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
                    time.sleep(.1)
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

    def query_neynar_api_for_users(self, fids):
        """
        Queries the Neynar API to get user objects for the given FIDs.
        """
        base_url = "https://api.neynar.com/v2/farcaster/user/bulk"
        headers = {
            "accept": "application/json",
            "api_key": self.NEYNAR_API_KEY
        }
        params = {
            "fids": ",".join(map(str, fids))
        }

        try:
            time.sleep(.1)
            response = r.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if 'users' not in data:
                print(f"Unexpected response format. Response: {data}")
            return data
        except RequestException as e:
            print(f"Error querying Neynar API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.content}")
            return None

    def is_data_stale(self, fid):
        """
        Checks if data for the given FID is missing or stale.
        """
        filepath = os.path.join(self.data_dir, f'user_{fid}.json')
        if not os.path.exists(filepath):
            return True 
        file_mod_time = os.path.getmtime(filepath)
        return (time.time() - file_mod_time) > self.max_age_seconds
    
    def collect_connections_ids(self, user_object):
        """
        Collects a unique list of all FIDs from the user object's attributes.
        
        Args:
            user_object (dict): A dictionary containing user data.
        
        Returns:
            set: A set of unique FIDs collected from the user object.
        """
        unique_fids = set()
        
        if 'core_node_metadata' in user_object and 'fid' in user_object['core_node_metadata']:
            unique_fids.add(user_object['core_node_metadata']['fid'])
        
        if 'follows' in user_object:
            unique_fids.update(follow['target'] for follow in user_object['follows'] if 'target' in follow)
        
        if 'followers' in user_object:
            unique_fids.update(follower['source'] for follower in user_object['followers'] if 'source' in follower)
        
        if 'likes' in user_object:
            unique_fids.update(like['target'] for like in user_object['likes'] if 'target' in like)
            unique_fids.update(like['source'] for like in user_object['likes'] if 'source' in like)
        
        if 'recasts' in user_object:
            unique_fids.update(recast['target'] for recast in user_object['recasts'] if 'target' in recast)
            unique_fids.update(recast['source'] for recast in user_object['recasts'] if 'source' in recast)
        
        if 'casts' in user_object:
            unique_fids.update(cast['target'] for cast in user_object['casts'] if 'target' in cast)
            unique_fids.update(cast['source'] for cast in user_object['casts'] if 'source' in cast)

        return unique_fids

    def get_user_metadata_for_connections(self, user_object):
        all_fids = list(self.collect_connections_ids(user_object))
        user_metadata_list = []

        # Process FIDs in batches of 100
        for i in range(0, len(all_fids), 100):
            batch = all_fids[i:i+100]
            response = self.query_neynar_api_for_users(batch)
            
            if response and 'users' in response:
                for user in response['users']:
                    user_metadata = {
                        'fid': str(user['fid']), ### lazy lazy
                        'username': user.get('username'),
                        'display_name': user.get('display_name'),
                        'pfp_url': user.get('pfp_url'),
                        'follower_count': user.get('follower_count'),
                        'following_count': user.get('following_count')
                    }
                    user_metadata_list.append(user_metadata)

        return user_metadata_list


    def get_user_metadata(self, fid):
        """Fetches user metadata for a single FID."""
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
                break  # Exit loop if we've found both bio and username

        return user_data
    
    def get_user_follows(self, fid):
        """Fetches users followed by provided Farcaster ID"""
        endpoint = "linksByFid"
        params = {
            'fid': str(fid), 
            'link_type': 'follow'
        }
        messages = self.query_neynar_hub(endpoint=endpoint, params=params)

        extracted_following = []
        for item in messages:
            if "data" in item and "linkBody" in item["data"]:
                target_fid = item['data']['linkBody'].get('targetFid')
                timestamp = item['data'].get('timestamp')
                if target_fid and timestamp:
                    extracted_following.append({
                        'source': str(fid),
                        'target': str(target_fid),
                        'timestamp': timestamp,
                        'edge_type': 'FOLLOWS'
                    })
        return extracted_following
    
    def get_user_followers(self, fid):
        """Fetches followers for provided Farcaster ID"""
        endpoint = "linksByTargetFid"
        params = {
            'link_type': 'follow', 
            'target_fid': fid
        }
        messages = self.query_neynar_hub(endpoint, params)

        extracted_followers = []
        for item in messages:
            if "data" in item and "linkBody" in item["data"]:
                follower_id = item['data'].get('fid')
                timestamp = item['data'].get('timestamp')
                if follower_id and timestamp:
                    extracted_followers.append({
                        'source': str(follower_id), 
                        'target': str(fid),
                        'timestamp': timestamp ,
                        'edge_type': 'FOLLOWS'
                    })

        return extracted_followers
    
    def get_user_likes(self, fid):
        """Fetches likes for provided Farcaster ID"""
        endpoint = "reactionsByFid"
        params = {
            'fid': fid,
            'reaction_type': 'REACTION_TYPE_LIKE'
        }
        messages = self.query_neynar_hub(endpoint, params)

        extracted_likes = []
        for item in messages:
            if "data" in item and "reactionBody" in item["data"]:
                target_cast = item['data']['reactionBody'].get('targetCastId')
                timestamp = item['data'].get('timestamp')
                if target_cast and timestamp:
                    extracted_likes.append({
                        'source': str(fid),
                        'target': str(target_cast.get('fid')),
                        'target_hash': target_cast.get('hash'),
                        'timestamp': timestamp,
                        'edge_type': 'LIKED'
                    })
        return extracted_likes

    def get_user_recasts(self, fid):
        """Fetches recasts for provided Farcaster ID"""
        endpoint = "reactionsByFid"
        params = {
            'fid': fid,
            'reaction_type': 'REACTION_TYPE_RECAST'
        }
        messages = self.query_neynar_hub(endpoint, params)

        extracted_recasts = []
        for item in messages:
            if "data" in item and "reactionBody" in item["data"]:
                target_cast = item['data']['reactionBody'].get('targetCastId')
                timestamp = item['data'].get('timestamp')
                if target_cast and timestamp:
                    extracted_recasts.append({
                        'source': str(fid),
                        'target': str(target_cast.get('fid')),
                        'target_hash': target_cast.get('hash'),
                        'timestamp': timestamp,
                        'edge_type': 'RECASTED'
                    })
        return extracted_recasts

    def get_user_casts(self, fid):
        print(f"Collecting casts for user {fid}.....")
        endpoint = "castsByFid"
        params = {'fid': fid}
        messages = self.query_neynar_hub(endpoint=endpoint, params=params)

        cast_data_list = []
        for message in messages:
            if 'data' in message and 'castAddBody' in message['data']:
                cast_add_body = message['data']['castAddBody']
                parent_cast = cast_add_body.get('parentCastId')
                if parent_cast:
                    cast_data = {
                        'source': str(fid),
                        'target': str(parent_cast['fid']),
                        'timestamp': message['data']['timestamp'],
                        'edge_type': 'REPLIED'
                    }
                    cast_data_list.append(cast_data)
        print(f"Retrieved {len(cast_data_list)} replies for user: {fid}...")
        return cast_data_list



    def get_user_data(self, fid):
            """Assembles all data for a single user."""
            likes = self.get_user_likes(fid)
            recasts = self.get_user_recasts(fid)
            casts = self.get_user_casts(fid)
            # followers = self.get_user_followers(fid)
            following = self.get_user_follows(fid)
            # followers = 
            # following =

            user_object = {
                'core_node_metadata': self.get_user_metadata(fid),
                'likes': likes,
                'recasts': recasts,
                'casts': casts,
                # 'followers': followers,
                'following': following
            }

            return user_object

    def get_all_users_data(self, fids):
            """Fetches and stores data for multiple users."""
            all_user_data = {}
            for fid in fids:
                print(f"Fetching data for FID: {fid}")
                user_data = self.get_user_data(fid)
                all_user_data[fid] = user_data

                # Optionally write to file if needed
                filename = f'user_{fid}_data.json'
                with open(os.path.join(self.data_dir, filename), 'w') as f:
                    json.dump(user_data, f)

            print("Finished fetching individual user data. Now collecting connection metadata...")

            # Collect connection metadata after fetching all individual user data
            for fid, user_data in all_user_data.items():
                print(f"Collecting connection metadata for FID: {fid}")
                connections_metadata = self.get_user_metadata_for_connections(user_data)
                user_data['connections_metadata'] = connections_metadata
                # Update the stored JSON file with the new data if needed
                filename = f'user_{fid}_data.json'
                with open(os.path.join(self.data_dir, filename), 'w') as f:
                    json.dump(user_data, f)

            return all_user_data            





    def upload_json_to_s3(self, data, s3_key):
        try:
            s3_client = boto3.client(
                's3',
                region_name='us-east-1',
                aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY
            )
            
            # Convert data to JSON string
            json_data = json.dumps(data)
            
            # Upload JSON data
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json',
                ACL='public-read'  # Makes the file publicly readable
            )
            
            print(f"Successfully uploaded {s3_key} to {self.bucket_name}")
            return True
        except (NoCredentialsError, ClientError) as e:
            print(f"Failed to upload {s3_key} to {self.bucket_name}. Error: {e}")
            return False



    # def get_all_users_data_s3(self, fids):
    #         """Fetches and stores data for multiple users in S3."""
    #         all_user_data = {}
    #         for fid in fids:
    #             print(f"Fetching data for FID: {fid}")
    #             user_data = self.get_user_data(fid)
    #             all_user_data[fid] = user_data

    #             # Upload individual user data to S3
    #             s3_key = f'user_{fid}_data.json'
    #             self.upload_json_to_s3(user_data, s3_key)

    #         print("Finished fetching individual user data. Now collecting connection metadata...")

    #         # # Collect connection metadata after fetching all individual user data
    #         # for fid, user_data in all_user_data.items():
    #         #     print(f"Collecting connection metadata for FID: {fid}")
    #         #     connections_metadata = self.get_user_metadata_for_connections(user_data)
    #         #     user_data['connections_metadata'] = connections_metadata
                
    #         #     # Update S3 with new data including connections metadata
    #         #     s3_key = f'user_{fid}_data.json'
    #         #     self.upload_json_to_s3(user_data, s3_key)

    #         return all_user_data


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
    lis = ['190000', '190001']
    fetcher.get_all_users_data_s3(lis)
    # fetcher = DataFetcher()
    # fetcher.get_user_data(['988', '378', '190000', '746'])
    # user_data = fetcher.fetch_and_store_user_data([5, 1677])
    # follows = fetcher.get_user_follows([3])
    # followers = fetcher.get_user_followers([190000])
    # likes = fetcher.get_user_likes([190000])
    # recasts = fetcher.get_user_recasts([3])
