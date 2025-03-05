# Subreddit Overlap Analyzer

A Python tool that analyzes the overlap of active users between different subreddits. This tool helps you understand the relationship between communities by identifying common participants.

## Features

- Collect active users from subreddits by scanning recent posts and comments
- Compare user bases between two subreddits to find overlaps
- Work with batches of users to handle large subreddits
- Cache results to avoid redundant API calls
- Interactive command-line interface
- Detailed statistics and overlap percentages
- Save results to JSON files for further analysis

## Requirements

- Python 3.6+
- Reddit API credentials (Client ID, Client Secret)

## Installation

### Step 1: Install Python 3

1. Visit the [Python downloads page](https://www.python.org/downloads/windows/)
2. Download the latest Python 3 installer (64-bit recommended)
3. Run the installer
4. **Important:** Check the box that says "Add Python to PATH"
5. Click "Install Now"
6. Wait for the installation to complete and click "Close"

### Step 2: Install Visual Studio Code (if not already installed)

1. Visit the [VSCode download page](https://code.visualstudio.com/download)
2. Download the Windows installer
3. Run the installer with default settings
4. Once installed, open VSCode

### Step 3: Clone the Repository

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/subredditOverlap.git
   cd subredditOverlap
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

```
python OverlApp.py [CLIENT_ID] [CLIENT_SECRET] [USER_AGENT]
```

You can either:
- Update the credentials directly in the script (not recommended for public repositories)
- Pass your credentials as command-line arguments
- Set up environment variables (see advanced configuration)

### Interactive Menu Options

1. **Compare two subreddits (first batch)**: Analyzes the initial batch of users from both subreddits
2. **Compare next batch**: Continues analysis with new users to increase the sample size
3. **Compare all saved batches**: Combines all previously collected data for a comprehensive analysis
4. **Quit**: Exit the program

### Example Workflow

1. Run option 1 to collect and compare the first batch of users from two subreddits
2. If more data is needed, run option 2 to collect additional batches
3. Use option 3 to get a comprehensive analysis of all collected data

## Data Storage

All data is stored in the `data` directory:
- User batches are saved as `{subreddit}_users_batch{N}_{timestamp}.json`
- Comparison results are saved as `{subreddit1}_vs_{subreddit2}_batch{N1}_{N2}_{timestamp}.json`
- Comprehensive comparisons are saved as `{subreddit1}_vs_{subreddit2}_all_batches_{timestamp}.json`

## Tips for Best Results

- Larger subreddits require more batches for accurate analysis
- Use the "Compare next batch" option to gather more user data
- The overlap percentage stabilizes with more data collection
- For very large subreddits, consider increasing the batch size

## Troubleshooting

- **Rate limiting errors**: Reddit limits API requests. If you encounter rate limiting, wait a few minutes before trying again.
- **No data directory**: If the `data` directory isn't created automatically, create it manually in the project root.
- **Authentication errors**: Double-check your Reddit API credentials.
- **Module not found errors**: Ensure you have activated your virtual environment and installed dependencies.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
