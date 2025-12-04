---
name: podcast-transcript
description: Extract and transcribe specific podcast episodes using local Whisper. Fetch episodes from RSS feeds, download audio, transcribe locally, and extract relevant transcript sections with context padding.
---

# Podcast Transcript Extraction Skill

## Overview

This skill enables you to extract relevant sections from podcast episodes. It fetches episodes from an RSS feed, transcribes them locally using OpenAI Whisper (no API calls), and returns the specific transcript excerpt you're looking for with surrounding context.

## Capabilities

- **RSS Feed Parsing**: Fetch episodes from any podcast RSS feed
- **Episode Selection**: Choose episodes by title or publication date
- **Local Transcription**: Use OpenAI Whisper for on-device transcription (no API required)
- **Smart Extraction**: Find transcript sections by timestamp or contextual description
- **Context Padding**: Return 30 seconds of surrounding content to ensure no gaps

## Usage

### Basic Workflow

1. **Provide Podcast Feed**: Supply the RSS feed URL
2. **Select Episode**: Choose episode by date or title (with user confirmation)
3. **Local Processing**: Downloads audio and transcribes locally
4. **Extract Section**: Specify what you're looking for (time range or quote context)
5. **Get Result**: Receive transcript excerpt with padding

### Example Scenarios

**Scenario 1: Find a specific quote**
```
/podcast-transcript
> Feed: https://example.com/podcast/feed.xml
> Title: "Episode 42: The Future of AI"
> Looking for: "discussion about neural networks"
```

**Scenario 2: Extract a time window**
```
/podcast-transcript
> Feed: https://example.com/podcast/feed.xml
> Title: "Recent Episode"
> Time window: 12:30 - 15:45
```

## Prerequisites

- Python 3.8+ installed locally
- OpenAI Whisper installed: `pip install openai-whisper`
- ffmpeg installed (for audio processing)
- curl or wget (for downloading audio files)

## Installation

```bash
# Install required Python packages
pip install feedparser requests pydub openai-whisper

# Install ffmpeg (on macOS)
brew install ffmpeg

# Install ffmpeg (on Ubuntu/Debian)
sudo apt-get install ffmpeg

# Install ffmpeg (on Windows)
choco install ffmpeg
```

## Output Format

The skill returns:
- Full transcript with timestamps
- Extracted section with context
- 30-second padding before and after target section
- Clear demarcation of request boundaries

## Limitations

- Transcription quality depends on audio quality and Whisper model
- Processing time scales with episode duration
- Large files may require significant disk space
- Some compressed audio formats may need pre-processing

## Technical Details

### Data Flow
1. Fetch and parse RSS feed using feedparser
2. Extract audio_enclosure_url from episode feed entries (required for audio file sourcing)
3. Display episodes to user for selection and confirmation
4. Download audio file from enclosure URL locally
5. Transcribe with Whisper model
6. Parse user's extraction request (timestamp or contextual quote)
7. Extract and format transcript section
8. Return result with 30-second context padding before and after

### Audio Enclosure Handling
The skill explicitly targets the `audio_enclosure_url` field from RSS feed entries. If feedparser does not automatically recognize the enclosure URL, the implementation falls back to:
- Checking standard RSS enclosure elements (`<enclosure>` tags)
- Parsing `media:content` elements
- Extracting from `link` fields as fallback

### Storage
- Temporary: Downloaded audio files stored in system temp directory
- Transcript: Returned to Claude context (not persisted)
- Cleanup: Audio files automatically removed after transcription

## Error Handling

- Invalid feed URL detection
- Episode not found handling
- Audio enclosure URL extraction and validation
- Download failure recovery
- Transcription error reporting
- User input validation
