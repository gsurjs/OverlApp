import praw
import json
import time
import os
import sys
from collections import defaultdict
from datetime import datetime

class SubredditOverlapAnalyzer:
    def __init__(self, client_id, client_secret, user_agent, username=None, password=None):
        """
        Initialize the Reddit API connection.
        
        Args:
            client_id (str): Reddit API client ID
            client_secret (str): Reddit API client secret
            user_agent (str): User agent string for API requests
            username (str, optional): Reddit username for authenticated requests
            password (str, optional): Reddit password for authenticated requests
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            username=username,
            password=password
        )
        
        # List of bot users to filter out
        self.bot_users = ["AutoModerator"]
        
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            
    def _get_timestamp(self):
        """Get current timestamp string for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _filter_bot_users(self, users_set):
        """
        Filter out known bot users from a set of usernames.
        
        Args:
            users_set (set): Set of usernames
            
        Returns:
            set: Filtered set of usernames with bots removed
        """
        return {user for user in users_set if user not in self.bot_users}
        
    def get_active_users(self, subreddit_name, post_limit=100, comment_limit=100, batch_size=1000, start_batch=0):
        """
        Get active users from a subreddit by scanning recent posts and comments in batches.
        
        Args:
            subreddit_name (str): Name of the subreddit to scan
            post_limit (int): Maximum number of posts to scan
            comment_limit (int): Maximum number of comments to scan per post
            batch_size (int): Maximum number of users to collect in one batch
            start_batch (int): Which batch to start from (0-indexed)
            
        Returns:
            dict: Dictionary containing user set, batch information, and whether there are more users
        """
        print(f"Collecting batch {start_batch+1} of users from r/{subreddit_name}...")
        users = set()
        subreddit = self.reddit.subreddit(subreddit_name)
        
        # If we're starting a fresh scan, use new posts
        # If we're continuing, use hot or top posts to get different users
        if start_batch == 0:
            submissions = subreddit.new(limit=None)
        elif start_batch == 1:
            submissions = subreddit.hot(limit=None)
        elif start_batch == 2:
            submissions = subreddit.top(time_filter="month", limit=None)
        elif start_batch == 3:
            submissions = subreddit.top(time_filter="year", limit=None)
        else:
            submissions = subreddit.top(time_filter="all", limit=None)
        
        post_count = 0
        reached_limit = False
        
        try:
            for submission in submissions:
                if post_count >= post_limit:
                    reached_limit = True
                    break
                    
                post_count += 1
                
                # Track post author - filter out bots like AutoModerator
                if submission.author and submission.author.name not in self.bot_users:
                    users.add(submission.author.name)
                
                # Get comment authors
                submission.comments.replace_more(limit=0)  # Flatten comment tree
                for comment in submission.comments.list()[:comment_limit]:
                    if comment.author and comment.author.name not in self.bot_users:
                        users.add(comment.author.name)
                        
                    # If we've reached our batch size, stop collecting
                    if len(users) >= batch_size:
                        reached_limit = True
                        break
                
                if reached_limit:
                    break
                    
                # Sleep to avoid rate limiting
                time.sleep(0.5)
                
                # Progress update
                if post_count % 10 == 0:
                    print(f"Processed {post_count} posts, found {len(users)} unique users")
                    
        except Exception as e:
            print(f"Error processing r/{subreddit_name}: {e}")
            
        # Determine if there are potentially more users to scan
        more_available = reached_limit
            
        result = {
            "users": users,
            "batch": start_batch + 1,
            "user_count": len(users),
            "more_available": more_available,
            "subreddit": subreddit_name
        }
        
        print(f"Finished batch {start_batch+1}: Found {len(users)} unique users in r/{subreddit_name}")
        return result
        
    def save_users_to_file(self, user_data):
        """
        Save a batch of users to a JSON file.
        
        Args:
            user_data (dict): Dictionary containing user set and batch information
            
        Returns:
            str: Filename where the data was saved
        """
        subreddit_name = user_data["subreddit"]
        batch = user_data["batch"]
        timestamp = self._get_timestamp()
        filename = f"data/{subreddit_name}_users_batch{batch}_{timestamp}.json"
        
        # Convert users set to list for JSON serialization
        save_data = user_data.copy()
        save_data["users"] = list(user_data["users"])
        
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)
            
        print(f"Saved {len(user_data['users'])} users to {filename}")
        return filename
        
    def load_users_from_file(self, filename):
        """
        Load users from a previously saved JSON file.
        
        Args:
            filename (str): Path to the JSON file
            
        Returns:
            dict: Dictionary containing user set and batch information
        """
        with open(filename, 'r') as f:
            data = json.load(f)
            
        # Convert users list back to set
        data["users"] = set(data["users"])
        
        # Filter out bot users from loaded data
        data["users"] = self._filter_bot_users(data["users"])
        
        print(f"Loaded {len(data['users'])} users from {filename}")
        return data
        
    def load_all_user_batches(self, subreddit_name):
        """
        Load all saved user batches for a subreddit.
        
        Args:
            subreddit_name (str): Name of the subreddit
            
        Returns:
            set: Combined set of all users from all batches
        """
        all_users = set()
        batch_files = []
        
        # Find all batch files for this subreddit
        for filename in os.listdir('data'):
            if filename.startswith(f"{subreddit_name}_users_batch") and filename.endswith('.json'):
                batch_files.append(os.path.join('data', filename))
                
        # Load and combine all batches
        for batch_file in batch_files:
            data = self.load_users_from_file(batch_file)
            all_users.update(data["users"])
            
        # Final filter for bot users in combined set
        all_users = self._filter_bot_users(all_users)
            
        print(f"Combined {len(batch_files)} batches for r/{subreddit_name}, total of {len(all_users)} unique users")
        return all_users
        
    def compare_subreddits_batch(self, subreddit1, subreddit2, post_limit=100, comment_limit=100, 
                               batch_size=1000, start_batch1=0, start_batch2=0, use_cache=False):
        """
        Compare users between two subreddits to find overlaps, working in batches.
        
        Args:
            subreddit1 (str): Name of the first subreddit
            subreddit2 (str): Name of the second subreddit
            post_limit (int): Maximum number of posts to scan in each subreddit
            comment_limit (int): Maximum number of comments to scan per post
            batch_size (int): Maximum number of users to collect in one batch
            start_batch1 (int): Which batch to start from for subreddit1
            start_batch2 (int): Which batch to start from for subreddit2
            use_cache (bool): Whether to use cached user data if available
            
        Returns:
            dict: Results containing user overlaps, statistics, and whether more batches are available
        """
        # Check if we have cached data for these batches
        batch1_file = None
        batch2_file = None
        
        if use_cache:
            # Look for the most recent batch files
            for filename in sorted(os.listdir('data'), reverse=True):
                if filename.startswith(f"{subreddit1}_users_batch{start_batch1+1}_") and not batch1_file:
                    batch1_file = os.path.join('data', filename)
                if filename.startswith(f"{subreddit2}_users_batch{start_batch2+1}_") and not batch2_file:
                    batch2_file = os.path.join('data', filename)
        
        # Get users from first subreddit
        if use_cache and batch1_file and os.path.exists(batch1_file):
            user_data1 = self.load_users_from_file(batch1_file)
            users1 = user_data1["users"]
            more_available1 = user_data1.get("more_available", False)
        else:
            user_data1 = self.get_active_users(subreddit1, post_limit, comment_limit, batch_size, start_batch1)
            users1 = user_data1["users"]
            more_available1 = user_data1["more_available"]
            self.save_users_to_file(user_data1)
            
        # Get users from second subreddit
        if use_cache and batch2_file and os.path.exists(batch2_file):
            user_data2 = self.load_users_from_file(batch2_file)
            users2 = user_data2["users"]
            more_available2 = user_data2.get("more_available", False)
        else:
            user_data2 = self.get_active_users(subreddit2, post_limit, comment_limit, batch_size, start_batch2)
            users2 = user_data2["users"]
            more_available2 = user_data2["more_available"]
            self.save_users_to_file(user_data2)
            
        # Find overlapping users
        overlapping_users = users1.intersection(users2)
        
        # Calculate statistics
        results = {
            "subreddit1": subreddit1,
            "subreddit2": subreddit2,
            "batch1": start_batch1 + 1,
            "batch2": start_batch2 + 1,
            "users_count1": len(users1),
            "users_count2": len(users2),
            "overlapping_users_count": len(overlapping_users),
            "overlapping_users": list(overlapping_users),
            "overlap_percentage1": round(len(overlapping_users) / len(users1) * 100, 2) if users1 else 0,
            "overlap_percentage2": round(len(overlapping_users) / len(users2) * 100, 2) if users2 else 0,
            "more_available1": more_available1,
            "more_available2": more_available2,
            "timestamp": self._get_timestamp()
        }
        
        # Save results
        results_filename = f"data/{subreddit1}_vs_{subreddit2}_batch{start_batch1+1}_{start_batch2+1}_{results['timestamp']}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        return results
        
    def compare_all_batches(self, subreddit1, subreddit2):
        """
        Compare all available batches between two subreddits.
        
        Args:
            subreddit1 (str): Name of the first subreddit
            subreddit2 (str): Name of the second subreddit
            
        Returns:
            dict: Results containing comprehensive overlap statistics
        """
        # Load all users from all batches
        all_users1 = self.load_all_user_batches(subreddit1)
        all_users2 = self.load_all_user_batches(subreddit2)
        
        # Find overlapping users
        overlapping_users = all_users1.intersection(all_users2)
        
        # Calculate statistics
        results = {
            "subreddit1": subreddit1,
            "subreddit2": subreddit2,
            "users_count1": len(all_users1),
            "users_count2": len(all_users2),
            "overlapping_users_count": len(overlapping_users),
            "overlapping_users": list(overlapping_users),
            "overlap_percentage1": round(len(overlapping_users) / len(all_users1) * 100, 2) if all_users1 else 0,
            "overlap_percentage2": round(len(overlapping_users) / len(all_users2) * 100, 2) if all_users2 else 0,
            "timestamp": self._get_timestamp()
        }
        
        # Save results
        results_filename = f"data/{subreddit1}_vs_{subreddit2}_all_batches_{results['timestamp']}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        return results
        
    def print_results(self, results):
        """
        Print formatted results of subreddit comparison.
        
        Args:
            results (dict): Results from compare_subreddits method
        """
        print("\n" + "="*60)
        
        if "batch1" in results:
            print(f"SUBREDDIT OVERLAP ANALYSIS - BATCH COMPARISON")
            print(f"r/{results['subreddit1']} (Batch {results['batch1']}) vs r/{results['subreddit2']} (Batch {results['batch2']})")
        else:
            print(f"SUBREDDIT OVERLAP ANALYSIS - ALL BATCHES")
            print(f"r/{results['subreddit1']} vs r/{results['subreddit2']}")
            
        print("="*60)
        print(f"Users in r/{results['subreddit1']}: {results['users_count1']}")
        print(f"Users in r/{results['subreddit2']}: {results['users_count2']}")
        print(f"Overlapping users: {results['overlapping_users_count']}")
        print(f"Percentage of r/{results['subreddit1']} users also in r/{results['subreddit2']}: {results['overlap_percentage1']}%")
        print(f"Percentage of r/{results['subreddit2']} users also in r/{results['subreddit1']}: {results['overlap_percentage2']}%")
        
        if "more_available1" in results and "more_available2" in results:
            print(f"\nMore users available to scan:")
            print(f"- r/{results['subreddit1']}: {'Yes' if results['more_available1'] else 'No'}")
            print(f"- r/{results['subreddit2']}: {'Yes' if results['more_available2'] else 'No'}")
        
        print("\nTop overlapping users:")
        
        # Show up to 10 overlapping users
        for i, user in enumerate(results['overlapping_users'][:100], 1):
            print(f"{i}. {user}")
            
        if results['overlapping_users_count'] > 100:
            print(f"... and {results['overlapping_users_count'] - 100} more")
            
        print("\nFull results saved to data directory")
        print("="*60)
        
    def send_messages_to_users(self, user_list, subject, message_body, min_throttle=3, max_throttle=8, 
                          daily_limit=50, batch_pause_min=30, messages_per_batch=10, simulate_natural=True):
        """
        Send a message to all users in the provided list with anti-spam measures.
        
        Args:
            user_list (list): List of usernames to message
            subject (str): Subject line for the message
            message_body (str): Body text of the message
            min_throttle (int): Minimum seconds to wait between messages
            max_throttle (int): Maximum seconds to wait between messages
            daily_limit (int): Maximum messages to send in a 24-hour period
            batch_pause_min (int): Minutes to pause after each batch
            messages_per_batch (int): Number of messages to send before taking a batch pause
            simulate_natural (bool): Whether to use varying delays to simulate natural messaging patterns
            
        Returns:
            dict: Results containing success and failure counts
        """
        # Filter out any bot users from the message list
        filtered_user_list = [user for user in user_list if user not in self.bot_users]
        
        if len(filtered_user_list) < len(user_list):
            print(f"Filtered out {len(user_list) - len(filtered_user_list)} bot users from messaging list")
            user_list = filtered_user_list
        
        # Check if we're authenticated without using user.me() which can fail with 401
        try:
            # Try a simple API call that requires auth
            self.reddit.auth.scopes()
            authenticated = True
        except Exception as e:
            authenticated = False
            print(f"Authentication error: {e}")
            
        if not authenticated:
            print("Error: You must be logged in to send messages. Please provide username and password when initializing.")
            return {
                "success_count": 0,
                "failed_count": len(user_list),
                "failed_users": user_list,
                "success_users": []
            }
            
        import random
        import datetime
        
        total_messages = len(user_list)
        days_needed = (total_messages + daily_limit - 1) // daily_limit
        
        print(f"Preparing to send messages to {total_messages} users...")
        if total_messages > daily_limit:
            print(f"With a daily limit of {daily_limit}, this will take approximately {days_needed} days to complete")
        print(f"Subject: {subject}")
        print(f"Message preview: {message_body[:50]}..." if len(message_body) > 50 else f"Message: {message_body}")
        print(f"Anti-spam settings:")
        print(f"- Wait time between messages: {min_throttle}-{max_throttle} seconds (randomized)")
        print(f"- Messages per batch: {messages_per_batch} before taking a {batch_pause_min} minute break")
        print(f"- Daily limit: {daily_limit} messages")
        print(f"- Natural timing simulation: {'On' if simulate_natural else 'Off'}")
        
        confirmation = input("\nAre you sure you want to proceed? This action cannot be undone. (y/n): ").lower()
        if confirmation != 'y':
            print("Message sending cancelled.")
            return {
                "success_count": 0,
                "failed_count": 0,
                "failed_users": [],
                "success_users": []
            }
            
        success_count = 0
        failed_count = 0
        failed_users = []
        success_users = []
        
        print("\nSending messages...")
        
        # Track daily message count and day start time
        day_start_time = datetime.datetime.now()
        daily_message_count = 0
        
        for i, username in enumerate(user_list, 1):
            # Check if we've hit daily limit
            current_time = datetime.datetime.now()
            time_since_day_start = (current_time - day_start_time).total_seconds()
            
            # If 24 hours haven't passed but we've hit our daily limit, wait until 24 hours from day start
            if daily_message_count >= daily_limit and time_since_day_start < 86400:  # 86400 seconds = 24 hours
                wait_seconds = 86400 - time_since_day_start
                next_batch_time = current_time + datetime.timedelta(seconds=wait_seconds)
                print(f"\nDaily limit of {daily_limit} messages reached. Waiting until {next_batch_time.strftime('%Y-%m-%d %H:%M:%S')} to continue...")
                
                # Save current progress before sleeping
                progress = {
                    "total_users": len(user_list),
                    "processed_count": i - 1,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "failed_users": failed_users,
                    "success_users": success_users,
                    "paused_until": next_batch_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "timestamp": self._get_timestamp()
                }
                
                progress_filename = f"data/message_progress_{progress['timestamp']}.json"
                with open(progress_filename, 'w') as f:
                    json.dump(progress, f, indent=2)
                    
                time.sleep(wait_seconds)
                
                # Reset daily counter and start time
                day_start_time = datetime.datetime.now()
                daily_message_count = 0
                print(f"Resuming messaging...")
            
            try:
                print(f"[{i}/{len(user_list)}] Sending message to u/{username}...", end="", flush=True)
                
                # Send the message
                self.reddit.redditor(username).message(subject, message_body)
                
                success_count += 1
                success_users.append(username)
                daily_message_count += 1
                print(" ✓")
                
                # Save progress periodically
                if i % 10 == 0:
                    progress = {
                        "total_users": len(user_list),
                        "processed_count": i,
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "failed_users": failed_users,
                        "success_users": success_users,
                        "daily_messages_sent": daily_message_count,
                        "daily_limit": daily_limit,
                        "day_start_time": day_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "timestamp": self._get_timestamp()
                    }
                    
                    progress_filename = f"data/message_progress_{progress['timestamp']}.json"
                    with open(progress_filename, 'w') as f:
                        json.dump(progress, f, indent=2)
                
                # Determine wait time between messages
                if simulate_natural:
                    # Occasionally have a longer pause to seem more human-like
                    if random.random() < 0.1:  # 10% chance of a longer pause
                        wait_time = random.uniform(max_throttle, max_throttle * 2)
                    else:
                        wait_time = random.uniform(min_throttle, max_throttle)
                else:
                    wait_time = random.uniform(min_throttle, max_throttle)
                
                # If we've completed a batch, take a longer pause
                if i % messages_per_batch == 0 and i < len(user_list):
                    batch_pause_sec = batch_pause_min * 60
                    batch_pause_with_jitter = random.uniform(batch_pause_sec * 0.8, batch_pause_sec * 1.2)
                    next_batch_time = datetime.datetime.now() + datetime.timedelta(seconds=batch_pause_with_jitter)
                    
                    print(f"\nCompleted batch of {messages_per_batch} messages. Taking a break until {next_batch_time.strftime('%H:%M:%S')}...")
                    time.sleep(batch_pause_with_jitter)
                    print("Resuming messaging...")
                else:
                    # Regular wait between messages
                    time.sleep(wait_time)
                
            except Exception as e:
                failed_count += 1
                failed_users.append(username)
                print(f" ✗ (Error: {str(e)})")
                
                # If we hit a rate limit, wait longer and extract wait time if possible
                if "RATELIMIT" in str(e).upper():
                    wait_time = 60  # Default wait time
                    try:
                        import re
                        match = re.search(r'(\d+) (minute|second)s', str(e))
                        if match:
                            num = int(match.group(1))
                            unit = match.group(2)
                            wait_time = num * 60 if unit == 'minute' else num
                    except:
                        pass
                        
                    next_attempt_time = datetime.datetime.now() + datetime.timedelta(seconds=wait_time)
                    print(f"Rate limit hit. Waiting until {next_attempt_time.strftime('%H:%M:%S')} before continuing...")
                    time.sleep(wait_time + random.uniform(10, 30))  # Add extra random buffer time
        
        # Save final results
        results = {
            "total_users": len(user_list),
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_users": failed_users,
            "success_users": success_users,
            "subject": subject,
            "message_body": message_body,
            "timestamp": self._get_timestamp()
        }
        
        results_filename = f"data/message_results_{results['timestamp']}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        print("\nMessage sending complete!")
        print(f"Successfully sent: {success_count}/{len(user_list)}")
        print(f"Failed: {failed_count}/{len(user_list)}")
        print(f"Results saved to {results_filename}")
        
        return results
    
    def load_overlap_results(self, subreddit1, subreddit2):
        """
        Load the most recent overlap results for two subreddits.
        
        Args:
            subreddit1 (str): Name of the first subreddit
            subreddit2 (str): Name of the second subreddit
            
        Returns:
            dict: The most recent overlap results, or None if not found
        """
        # First try to find all batches results
        all_batches_pattern = f"{subreddit1}_vs_{subreddit2}_all_batches_"
        reverse_all_batches_pattern = f"{subreddit2}_vs_{subreddit1}_all_batches_"
        
        # Then look for individual batch results
        batch_pattern = f"{subreddit1}_vs_{subreddit2}_batch"
        reverse_batch_pattern = f"{subreddit2}_vs_{subreddit1}_batch"
        
        most_recent_file = None
        most_recent_time = 0
        
        for filename in os.listdir('data'):
            filepath = os.path.join('data', filename)
            if (filename.startswith(all_batches_pattern) or 
                filename.startswith(reverse_all_batches_pattern) or
                filename.startswith(batch_pattern) or
                filename.startswith(reverse_batch_pattern)) and filename.endswith('.json'):
                
                file_time = os.path.getmtime(filepath)
                if file_time > most_recent_time:
                    most_recent_time = file_time
                    most_recent_file = filepath
        
        if most_recent_file:
            with open(most_recent_file, 'r') as f:
                results = json.load(f)
            print(f"Loaded overlap results from {most_recent_file}")
            return results
        else:
            print(f"No overlap results found for r/{subreddit1} and r/{subreddit2}")
            return None


def interactive_menu(analyzer):
    """
    Interactive menu for comparing subreddits in batches.
    """
    ascii_art = r"""
      ____          _     _ _ _                  
     |  _ \ ___  __| | __| (_) |_                
     | |_) / _ \/ _` |/ _` | | __|               
     |  _ <  __/ (_| | (_| | | |_                
     |_|_\_\___|\__,_|\__,_|_|\__|               
      / _ \__   _____ _ __| |  / \   _ __  _ __  
     | | | \ \ / / _ \ '__| | / _ \ | '_ \| '_ \ 
     | |_| |\ V /  __/ |  | |/ ___ \| |_) | |_) |
      \___/  \_/ \___|_|  |_/_/   \_\ .__/| .__/ 
                                    |_|   |_|    
    """
    while True:
        print("\n" + "="*60)
        print(ascii_art)
        print("="*60)
        print("1. Compare two subreddits (first batch of 1000 users)")
        print("2. Compare next batch")
        print("3. Compare all saved batches")
        print("4. Message overlapping users")
        print("5. Quit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == '1':
            subreddit1 = input("Enter first subreddit name: ")
            subreddit2 = input("Enter second subreddit name: ")
            
            post_limit = int(input("Enter max posts to scan per subreddit (default 100): ") or "100")
            comment_limit = int(input("Enter max comments to scan per post (default 50): ") or "50")
            batch_size = int(input("Enter batch size (default 1000): ") or "1000")
            
            results = analyzer.compare_subreddits_batch(
                subreddit1=subreddit1,
                subreddit2=subreddit2,
                post_limit=post_limit,
                comment_limit=comment_limit,
                batch_size=batch_size,
                start_batch1=0,
                start_batch2=0
            )
            
            analyzer.print_results(results)
            
        elif choice == '2':
            subreddit1 = input("Enter first subreddit name: ")
            subreddit2 = input("Enter second subreddit name: ")
            
            # Find the highest batch numbers
            batch1 = 0
            batch2 = 0
            for filename in os.listdir('data'):
                if filename.startswith(f"{subreddit1}_users_batch"):
                    try:
                        current_batch = int(filename.split('_batch')[1].split('_')[0])
                        batch1 = max(batch1, current_batch)
                    except:
                        pass
                        
                if filename.startswith(f"{subreddit2}_users_batch"):
                    try:
                        current_batch = int(filename.split('_batch')[1].split('_')[0])
                        batch2 = max(batch2, current_batch)
                    except:
                        pass
            
            print(f"Found existing batches: r/{subreddit1} (Batch {batch1}), r/{subreddit2} (Batch {batch2})")
            use_existing = input(f"Start from the next batch? (y/n, default: y): ").lower() != 'n'
            
            if use_existing:
                start_batch1 = batch1
                start_batch2 = batch2
            else:
                start_batch1 = int(input(f"Enter starting batch for r/{subreddit1} (0-indexed): "))
                start_batch2 = int(input(f"Enter starting batch for r/{subreddit2} (0-indexed): "))
            
            post_limit = int(input("Enter max posts to scan per subreddit (default 100): ") or "100")
            comment_limit = int(input("Enter max comments to scan per post (default 50): ") or "50")
            batch_size = int(input("Enter batch size (default 1000): ") or "1000")
            
            results = analyzer.compare_subreddits_batch(
                subreddit1=subreddit1,
                subreddit2=subreddit2,
                post_limit=post_limit,
                comment_limit=comment_limit,
                batch_size=batch_size,
                start_batch1=start_batch1,
                start_batch2=start_batch2
            )
            
            analyzer.print_results(results)
            
        elif choice == '3':
            subreddit1 = input("Enter first subreddit name: ")
            subreddit2 = input("Enter second subreddit name: ")
            
            # Check if we have batches for these subreddits
            has_batches1 = False
            has_batches2 = False
            
            for filename in os.listdir('data'):
                if filename.startswith(f"{subreddit1}_users_batch"):
                    has_batches1 = True
                if filename.startswith(f"{subreddit2}_users_batch"):
                    has_batches2 = True
            
            if not has_batches1 or not has_batches2:
                print(f"Error: Missing batch data for one or both subreddits.")
                print(f"r/{subreddit1} data found: {has_batches1}")
                print(f"r/{subreddit2} data found: {has_batches2}")
                print("Please run option 1 or 2 first to collect some data.")
                continue
                
            results = analyzer.compare_all_batches(subreddit1, subreddit2)
            analyzer.print_results(results)

        elif choice == '4':
            # Check if we're authenticated without using user.me() which can fail with 401
            try:
                # Try a simple API call that requires auth
                analyzer.reddit.auth.scopes()
                authenticated = True
            except Exception as e:
                authenticated = False
                print(f"Authentication error: {e}")
                
            if not authenticated:
                print("Error: You must be logged in to send messages.")
                print("Please restart the program with your Reddit username and password.")
                continue
                
            subreddit1 = input("Enter first subreddit name: ")
            subreddit2 = input("Enter second subreddit name: ")
            
            # Load the most recent overlap results
            results = analyzer.load_overlap_results(subreddit1, subreddit2)
            
            if not results:
                print("No overlap results found. Please run a comparison first.")
                continue
                
            # Get user list
            if not results.get("overlapping_users"):
                print("No overlapping users found in the results.")
                continue
                
            users = results["overlapping_users"]
            
            # Message options
            print(f"\nFound {len(users)} overlapping users between r/{results['subreddit1']} and r/{results['subreddit2']}")
            
            limit_input = input("How many users to message? (default: all): ")
            user_limit = int(limit_input) if limit_input.isdigit() else len(users)
            users = users[:user_limit]
            
            # Get message content
            print("\nEnter message subject:")
            subject = input("> ")
            
            print("\nEnter message body (type 'END' on a new line when finished):")
            lines = []
            while True:
                line = input()
                if line == 'END':
                    break
                lines.append(line)
            message_body = '\n'.join(lines)
            
            # Anti-spam settings
            print("\n=== Anti-Spam Configuration ===")
            min_throttle = int(input("Minimum seconds between messages (default: 3): ") or "3")
            max_throttle = int(input("Maximum seconds between messages (default: 8): ") or "8")
            daily_limit = int(input("Maximum messages per day (default: 50): ") or "50")
            messages_per_batch = int(input("Messages per batch before taking a break (default: 10): ") or "10")
            batch_pause_min = int(input("Minutes to pause between batches (default: 30): ") or "30")
            simulate_natural = input("Simulate natural messaging patterns? (y/n, default: y): ").lower() != 'n'
            
            # Send messages
            results = analyzer.send_messages_to_users(
                users, 
                subject, 
                message_body, 
                min_throttle=min_throttle,
                max_throttle=max_throttle,
                daily_limit=daily_limit,
                batch_pause_min=batch_pause_min,
                messages_per_batch=messages_per_batch,
                simulate_natural=simulate_natural
            )
            
        elif choice == '5':
            print("Exiting. Thanks for using the Subreddit Overlap Analyzer!")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")


# Main function
def main():
    # Replace with your Reddit API credentials
    CLIENT_ID = "Paste Your Client ID Here"
    CLIENT_SECRET = "Paste Your Client Secret Here"
    USER_AGENT = "Paste Your User Agent Here"
    USERNAME = None  # Required for sending messages
    PASSWORD = None  # Required for sending messages
    
    # Check for command-line credentials
    if len(sys.argv) >= 4:
        CLIENT_ID = sys.argv[1]
        CLIENT_SECRET = sys.argv[2]
        USER_AGENT = sys.argv[3]
        
        # Optional username and password for auth
        if len(sys.argv) >= 6:
            USERNAME = sys.argv[4]
            PASSWORD = sys.argv[5]
    
    # If not provided in command line, prompt for them if sending messages is desired
    if not USERNAME or not PASSWORD:
        print("NOTE: Reddit username and password are required for sending messages.")
        print("Without these credentials, you can still analyze subreddits but not send messages.")
        print("If you want to send messages later, restart the program with credentials.")
        
        auth_now = input("Would you like to provide credentials now? (y/n): ").lower() == 'y'
        if auth_now:
            USERNAME = input("Enter your Reddit username: ")
            PASSWORD = input("Enter your Reddit password: ")
    
    # Initialize the analyzer
    analyzer = SubredditOverlapAnalyzer(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
        username=USERNAME,
        password=PASSWORD
    )
    
    # Launch the interactive menu
    interactive_menu(analyzer)


if __name__ == "__main__":
    main()