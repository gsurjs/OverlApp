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
        
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            
    def _get_timestamp(self):
        """Get current timestamp string for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
                
                # Track post author
                if submission.author:
                    users.add(submission.author.name)
                
                # Get comment authors
                submission.comments.replace_more(limit=0)  # Flatten comment tree
                for comment in submission.comments.list()[:comment_limit]:
                    if comment.author:
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


def interactive_menu(analyzer):
    """
    Interactive menu for comparing subreddits in batches.
    """
    while True:
        print("\n" + "="*60)
        print("SUBREDDIT OVERLAP ANALYZER")
        print("="*60)
        print("1. Compare two subreddits (first batch of 1000 users)")
        print("2. Compare next batch")
        print("3. Compare all saved batches")
        print("4. Quit")
        
        choice = input("\nEnter your choice (1-4): ")
        
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
            print("Exiting. Thanks for using the Subreddit Overlap Analyzer!")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")


# Main function
def main():
    # Replace with your Reddit API credentials
    CLIENT_ID = "Paste Your Client ID Here"
    CLIENT_SECRET = "Paste Your Client Secret Here"
    USER_AGENT = "Paste Your User Agent Here"
    
    # Check for command-line credentials
    if len(sys.argv) >= 4:
        CLIENT_ID = sys.argv[1]
        CLIENT_SECRET = sys.argv[2]
        USER_AGENT = sys.argv[3]
    
    # Initialize the analyzer
    analyzer = SubredditOverlapAnalyzer(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    
    # Launch the interactive menu
    interactive_menu(analyzer)


if __name__ == "__main__":
    main()
