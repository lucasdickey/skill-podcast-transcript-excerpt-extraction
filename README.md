# Podcast Transcript Excerpt Extraction Skill

Extract and transcribe specific podcast episodes using local OpenAI Whisper. This skill fetches episodes from RSS feeds, downloads audio locally, transcribes with Whisper, and returns the exact transcript excerpt you're looking for with surrounding context.

## Features

- 🎙️ **RSS Feed Integration**: Fetch episodes from any podcast RSS feed
- 📥 **Local Processing**: Download and transcribe audio on your machine (no API calls)
- 🎯 **Flexible Extraction**: Get transcripts by timestamp window or contextual search
- ⏱️ **Context Padding**: Automatically include 30 seconds before and after to avoid gaps
- ✅ **User Confirmation**: Review and confirm episodes before downloading
- 💾 **Audio Enclosure Handling**: Explicit extraction of audio URLs from feed entries

## Quick Start

### Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install system dependencies:**

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
```bash
choco install ffmpeg
```

### Usage

Run the script directly:
```bash
python3 podcast_transcript.py
```

Then follow the interactive prompts:

1. **Provide the podcast RSS feed URL**
   - Example: `https://feeds.example.com/podcast.xml`

2. **Select an episode** by:
   - Episode number (from the displayed list)
   - Episode title
   - Publication date (YYYY-MM-DD)

3. **Confirm your selection**
   - Review the episode details before proceeding

4. **Choose extraction method:**
   - **Timestamp**: Specify start and end times (MM:SS or HH:MM:SS)
   - **Context**: Describe what you're looking for (quote, topic, etc.)

5. **Get your transcript extract** with 30-second padding on both sides

6. **Optionally save** the transcript to a file

## Example Scenarios

### Extract by Timestamp
```
Feed URL: https://example.com/podcast.xml
Episode: "Episode 42: The Future of AI"
Start: 12:30
End: 15:45
```

### Extract by Context
```
Feed URL: https://example.com/podcast.xml
Episode: "Recent Episode"
Search: "discussion about neural networks"
```

## How It Works

1. **Fetch Feed**: Downloads and parses the RSS feed
2. **Extract Audio URL**: Retrieves `audio_enclosure_url` from feed entries
3. **Download**: Fetches audio file to temporary directory
4. **Transcribe**: Uses Whisper to transcribe locally
5. **Extract**: Finds and returns the requested section with context padding
6. **Cleanup**: Removes temporary audio files

## Audio Enclosure Handling

The skill explicitly targets the `audio_enclosure_url` field. If feedparser doesn't automatically recognize it, the implementation falls back to:

- Standard RSS `<enclosure>` tags
- `media:content` elements
- Direct `link` fields
- Fallback to `audio_enclosure_url` attribute

## Output Format

```
================================================================================
TRANSCRIPT EXTRACT
================================================================================

Target window: 123.4s - 234.5s
With 30s padding: 93.4s - 264.5s

--------------------------------------------------------------------------------
>>> [123.4s - 123.8s] This is the exact section you requested
    [125.0s - 126.5s] Additional context before the target
    [127.0s - 128.3s] More context after the target
--------------------------------------------------------------------------------
```

## Whisper Models

The script uses Whisper's "base" model by default. You can modify the model size:

- `tiny`: Smallest, fastest
- `base`: Good balance (default)
- `small`: Better accuracy
- `medium`: High accuracy
- `large`: Best accuracy (requires more resources)

Edit `podcast_transcript.py` line ~169 to change:
```python
transcript = extractor.transcribe_audio(audio_path, model_name="base")
```

## Requirements

- Python 3.8+
- ffmpeg
- feedparser
- requests
- openai-whisper

See `requirements.txt` for pinned versions.

## Limitations

- Transcription quality depends on audio quality
- Processing time scales with episode duration (base model: ~1min per min of audio)
- Large files may require significant disk space temporarily
- Some compressed audio formats may need pre-processing
- Whisper model files are downloaded on first use (~140MB for base)

## Storage & Privacy

- **Downloaded audio**: Stored temporarily in system temp directory
- **Transcripts**: Returned to context (not saved unless you choose to)
- **Auto cleanup**: Audio files automatically removed after transcription
- **No external calls**: Everything runs locally (except initial RSS fetch)

## Troubleshooting

### "Failed to parse feed"
- Verify the RSS URL is correct
- Check if the feed is publicly accessible
- Some feeds require specific headers

### "No audio enclosure found"
- Not all podcasts include audio in enclosures
- Some use alternative feed formats
- Try a different podcast

### "Transcription takes very long"
- Switch to a smaller Whisper model (`tiny` or `small`)
- This will be faster but potentially less accurate

### Memory errors
- Use a smaller Whisper model
- Process shorter episodes first

## Use Cases

- 📰 **Content curation**: Extract key moments from interview podcasts
- 🎓 **Learning**: Find specific explanations or definitions
- 📝 **Citation**: Get exact quotes with timestamps
- 🔍 **Research**: Pull relevant sections from multiple episodes
- 💬 **Sharing**: Extract shareable transcript snippets

## API vs Local

This skill uses **local Whisper** exclusively for privacy and security:
- ✅ No data sent to external APIs
- ✅ No rate limits
- ✅ Works offline (after model download)
- ✅ Complies with company security policies

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## Author

Created as a Claude Code skill for podcast transcript extraction and analysis.
