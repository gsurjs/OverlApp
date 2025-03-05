# Subreddit Overlap Analyzer

A Python tool that analyzes the overlap of active users between different subreddits. This tool helps you find common Redditors between communities, assisting in networking opportunities.

## Features

- Collect active users from subreddits by scanning recent posts and comments
- Compare user bases between two subreddits to find overlaps
- Work with batches of users to handle large subreddits
- Cache results to avoid redundant API calls
- **NEW: Send messages to users who participate in both subreddits**
- Interactive command-line interface
- Detailed statistics and overlap percentages
- Save results to JSON files for further analysis

## Requirements

- Python 3.6+
- Reddit API credentials (Client ID, Client Secret)
- Reddit account credentials (for messaging feature)

## Installation

### Step 1: Install Python 3

1. Visit the [Python downloads page](https://www.python.org/downloads/)
2. Download the latest Python 3 installer (64-bit recommended)
3. Run the installer

### Step 2: Clone the Repository

1. Clone this repository:
   ```
   git clone https://github.com/gsurjs/OverlApp.git
   cd OverlApp
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Getting Reddit API Credentials

Before using this tool, you'll need to register for Reddit API credentials:

1. Visit [Reddit's App Preferences](https://www.reddit.com/prefs/apps)
2. Scroll down and click "Create app" or "Create another app"
3. Fill in the details:
   - Name: SubredditOverlapAnalyzer (or any name you prefer)
   - App type: Select "script"
   - Description: Optional
   - About URL: Optional
   - Redirect URI: http://localhost:8080 (this won't be used, but is required)
4. Click "Create app"
5. Note down your Client ID (the string under the app name) and Client Secret

## Usage

### Run with Interactive Menu

(make sure each argument is passed in as a string ie "1234abcd" for [CLIENT_ID] etc)

```
python OverlApp.py [CLIENT_ID] [CLIENT_SECRET] [USER_AGENT] [USERNAME] [PASSWORD]
```

You can either:
- Update the credentials directly in the script (not recommended for public repositories)
- Pass your credentials as command-line arguments (including username and password for messaging)
- Set up environment variables (see advanced configuration)

### Interactive Menu Options

1. **Compare two subreddits (first batch)**: Analyzes the initial batch of users from both subreddits
2. **Compare next batch**: Continues analysis with new users to increase the sample size
3. **Compare all saved batches**: Combines all previously collected data for a comprehensive analysis
4. **Message overlapping users**: Send messages to users who participate in both subreddits
5. **Quit**: Exit the program

### Example Workflow

1. Run option 1 to collect and compare the first batch of users from two subreddits
2. If more data is needed, run option 2 to collect additional batches
3. Use option 3 to get a comprehensive analysis of all collected data
4. Optionally, use option 4 to message users who participate in both communities

## Using the Messaging Feature

The messaging feature allows you to reach out to users who are active in both subreddits. This could be useful for:
- Community announcements
- Research purposes
- Invitations to related communities
- Feedback collection

### Requirements for Messaging

- You must provide your Reddit username and password when starting the program
- Your Reddit account must have sufficient age and karma to send messages
- The script includes throttling to comply with Reddit's rate limits

### How to Use the Messaging Feature

1. Run the program with your Reddit credentials (make sure they're passed as strings aka surrounded in ""):
   ```
   python OverlApp.py "CLIENT_ID" "CLIENT_SECRET" "USER_AGENT" "USERNAME" "PASSWORD"
   ```

2. Complete at least one comparison between two subreddits (options 1, 2, or 3)

3. Select option 4 "Message overlapping users" from the menu

4. Enter the names of the two subreddits you've previously compared

5. Choose how many users to message (defaults to all overlapping users)

6. Enter a subject line for your message

7. Type your message body (type 'END' on a new line when finished)

8. Set the throttle time between messages (default: 3 seconds, recommended: 3-5 seconds)

9. Confirm to begin sending messages

### Important Considerations for Messaging

- **Use Responsibly**: Mass messaging can be considered spam if misused
- **Reddit Rate Limits**: Reddit limits how many messages you can send per hour
- **Account Safety**: Excessive messaging could lead to account restrictions
- **Ethical Usage**: Always be respectful and provide value to recipients
- **Progress Tracking**: The program saves progress and results to the data directory

## Data Storage

All data is stored in the `data` directory:
- User batches are saved as `{subreddit}_users_batch{N}_{timestamp}.json`
- Comparison results are saved as `{subreddit1}_vs_{subreddit2}_batch{N1}_{N2}_{timestamp}.json`
- Comprehensive comparisons are saved as `{subreddit1}_vs_{subreddit2}_all_batches_{timestamp}.json`
- Messaging results are saved as `message_results_{timestamp}.json`
- Messaging progress is saved as `message_progress_{timestamp}.json`

## Tips for Best Results

- Larger subreddits require more batches for accurate analysis
- Use the "Compare next batch" option to gather more user data
- The overlap percentage stabilizes with more data collection
- For very large subreddits, consider increasing the batch size
- When messaging, use a higher throttle time (5-10 seconds) for better success rates

## Troubleshooting

- **Rate limiting errors**: Reddit limits API requests. If you encounter rate limiting, wait a few minutes before trying again.
- **No data directory**: If the `data` directory isn't created automatically, create it manually in the project root.
- **Authentication errors**: Double-check your Reddit API credentials.
- **Module not found errors**: Ensure you have activated your virtual environment and installed dependencies.
- **Messaging errors**: If you can't send messages, verify that your account meets Reddit's requirements for sending messages.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
