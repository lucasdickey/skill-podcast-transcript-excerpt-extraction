#!/usr/bin/env python3
"""
Podcast Transcript Extraction Skill
Fetches podcast episodes from RSS feeds, transcribes them locally with Whisper,
and extracts relevant transcript sections with context padding.
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import re

try:
    import feedparser
    import requests
    import whisper
except ImportError as e:
    print(f"Error: Missing required package. Install with: pip install feedparser requests openai-whisper")
    sys.exit(1)


class PodcastTranscriptExtractor:
    """Main class for podcast transcription and extraction."""

    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize the extractor.

        Args:
            temp_dir: Directory for temporary files. Uses system temp if not provided.
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "podcast_transcripts"
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.whisper_model = None

    def fetch_feed(self, feed_url: str) -> Dict:
        """Fetch and parse RSS feed.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            Parsed feed dictionary
        """
        print(f"Fetching feed from: {feed_url}")
        feed = feedparser.parse(feed_url)

        if feed.bozo and isinstance(feed.bozo_exception, Exception):
            raise ValueError(f"Failed to parse feed: {feed.bozo_exception}")

        return feed

    def extract_audio_url(self, entry: Dict) -> Optional[str]:
        """Extract audio enclosure URL from feed entry.

        Args:
            entry: Feed entry from feedparser

        Returns:
            Audio URL or None if not found
        """
        # Try standard enclosure first
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'audio' in enclosure.get('type', '').lower():
                    return enclosure.get('href')

        # Try media:content
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'audio' in media.get('type', '').lower():
                    return media.get('url')

        # Try links
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').lower().startswith('audio'):
                    return link.get('href')

        # Last resort: check for audio_enclosure_url attribute
        if hasattr(entry, 'audio_enclosure_url'):
            return entry.audio_enclosure_url

        return None

    def display_episodes(self, feed: Dict) -> None:
        """Display available episodes to user."""
        print("\nAvailable episodes:")
        print("-" * 80)

        for idx, entry in enumerate(feed.entries[:20], 1):  # Show last 20 episodes
            title = entry.get('title', 'Unknown')
            published = entry.get('published', 'Unknown')
            audio_url = self.extract_audio_url(entry)

            # Format published date if available
            pub_date_str = published
            if published != 'Unknown':
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(published)
                    pub_date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass

            audio_status = "✓" if audio_url else "✗"
            print(f"{idx:2d}. [{audio_status}] {title}")
            print(f"    Published: {pub_date_str}")
            print()

    def select_episode(self, feed: Dict, query: Optional[str] = None) -> Tuple[Dict, int]:
        """Select an episode by title or index.

        Args:
            feed: Parsed feed dictionary
            query: Search query (episode title, index, or date)

        Returns:
            Tuple of (entry, index)
        """
        entries = feed.entries

        if not entries:
            raise ValueError("No episodes found in feed")

        # If no query provided, display options
        if query is None:
            self.display_episodes(feed)
            selection = input("\nEnter episode number, title, or date (YYYY-MM-DD): ").strip()
        else:
            selection = query

        # Try numeric selection
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(entries):
                return entries[idx], idx
        except ValueError:
            pass

        # Try title/date search
        search_lower = selection.lower()
        for idx, entry in enumerate(entries):
            title = entry.get('title', '').lower()
            published = entry.get('published', '')

            if search_lower in title or search_lower in published:
                return entry, idx

        raise ValueError(f"Episode not found: {selection}")

    def confirm_selection(self, entry: Dict) -> bool:
        """Get user confirmation for selected episode.

        Args:
            entry: Feed entry

        Returns:
            True if user confirms, False otherwise
        """
        title = entry.get('title', 'Unknown')
        published = entry.get('published', 'Unknown')
        audio_url = self.extract_audio_url(entry)

        print("\nSelected episode:")
        print("-" * 80)
        print(f"Title: {title}")
        print(f"Published: {published}")
        print(f"Audio available: {'Yes' if audio_url else 'No'}")

        if not audio_url:
            print("Warning: No audio URL found in this episode!")

        print()
        response = input("Proceed with this episode? (y/n): ").strip().lower()
        return response in ('y', 'yes')

    def download_audio(self, audio_url: str, episode_title: str) -> Path:
        """Download audio file locally.

        Args:
            audio_url: URL of audio file
            episode_title: Episode title for file naming

        Returns:
            Path to downloaded file
        """
        print(f"\nDownloading audio from: {audio_url}")

        # Create safe filename
        safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length

        # Determine file extension from URL
        ext = '.mp3'  # default
        if '.' in audio_url.split('?')[0]:
            ext = '.' + audio_url.split('.')[-1].split('?')[0]

        audio_path = self.temp_dir / f"{safe_title}{ext}"

        try:
            response = requests.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = (downloaded / total_size) * 100
                            print(f"Downloaded: {pct:.1f}%", end='\r')

            print(f"Downloaded to: {audio_path}")
            return audio_path

        except Exception as e:
            raise RuntimeError(f"Failed to download audio: {e}")

    def transcribe_audio(self, audio_path: Path, model_name: str = "base") -> Dict:
        """Transcribe audio using Whisper.

        Args:
            audio_path: Path to audio file
            model_name: Whisper model size (tiny, base, small, medium, large)

        Returns:
            Transcription dictionary with segments and text
        """
        print(f"\nLoading Whisper model: {model_name}")

        if self.whisper_model is None:
            self.whisper_model = whisper.load_model(model_name)

        print(f"Transcribing audio file: {audio_path}")
        result = self.whisper_model.transcribe(str(audio_path), verbose=True)

        return result

    def parse_timestamp(self, timestamp_str: str) -> float:
        """Parse timestamp string to seconds.

        Args:
            timestamp_str: Time string (MM:SS or HH:MM:SS)

        Returns:
            Time in seconds
        """
        parts = timestamp_str.strip().split(':')

        if len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")

    def extract_by_timestamp(self, transcript: Dict, start_time: float, end_time: float, padding: int = 30) -> str:
        """Extract transcript section by timestamp.

        Args:
            transcript: Whisper transcription result
            start_time: Start time in seconds
            end_time: End time in seconds
            padding: Seconds of padding before/after

        Returns:
            Extracted transcript text with padding
        """
        segments = transcript.get('segments', [])

        # Apply padding
        padded_start = max(0, start_time - padding)
        padded_end = end_time + padding

        extracted_segments = []
        for segment in segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)

            if seg_end >= padded_start and seg_start <= padded_end:
                extracted_segments.append(segment)

        # Format output
        output = []
        output.append("=" * 80)
        output.append("TRANSCRIPT EXTRACT")
        output.append("=" * 80)
        output.append(f"\nTarget window: {start_time:.1f}s - {end_time:.1f}s")
        output.append(f"With {padding}s padding: {padded_start:.1f}s - {padded_end:.1f}s\n")
        output.append("-" * 80)

        for segment in extracted_segments:
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()

            # Highlight target section
            in_target = start >= start_time and end <= end_time
            marker = ">>>" if in_target else "   "

            output.append(f"{marker} [{start:6.1f}s - {end:6.1f}s] {text}")

        output.append("-" * 80)

        return "\n".join(output)

    def extract_by_context(self, transcript: Dict, context: str, padding: int = 30) -> str:
        """Extract transcript section by contextual search.

        Args:
            transcript: Whisper transcription result
            context: Text to search for
            padding: Seconds of padding before/after

        Returns:
            Extracted transcript text with padding
        """
        segments = transcript.get('segments', [])
        full_text = transcript.get('text', '')

        # Find context in transcript
        context_lower = context.lower()
        full_text_lower = full_text.lower()

        match_pos = full_text_lower.find(context_lower)
        if match_pos == -1:
            return f"Context not found in transcript: {context}"

        # Find segments containing the match
        char_count = 0
        start_segment_idx = None
        end_segment_idx = None

        for idx, segment in enumerate(segments):
            text = segment.get('text', '')
            char_count += len(text)

            if char_count >= match_pos and start_segment_idx is None:
                start_segment_idx = max(0, idx - 1)

            if char_count >= match_pos + len(context):
                end_segment_idx = min(len(segments) - 1, idx + 1)
                break

        if start_segment_idx is None or end_segment_idx is None:
            return f"Could not locate context in segments"

        # Apply padding
        start_time = segments[start_segment_idx].get('start', 0) - padding
        end_time = segments[end_segment_idx].get('end', 0) + padding
        start_time = max(0, start_time)

        # Extract segments
        extracted_segments = []
        for segment in segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)

            if seg_end >= start_time and seg_start <= end_time:
                extracted_segments.append(segment)

        # Format output
        output = []
        output.append("=" * 80)
        output.append("TRANSCRIPT EXTRACT")
        output.append("=" * 80)
        output.append(f"\nSearching for: \"{context}\"")
        output.append(f"With {padding}s padding\n")
        output.append("-" * 80)

        for segment in extracted_segments:
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()

            # Highlight matching text
            if context_lower in text.lower():
                # Use regex for case-insensitive replacement
                text_highlighted = re.sub(
                    f'({re.escape(context)})',
                    r'>>> \1 <<<',
                    text,
                    flags=re.IGNORECASE
                )
            else:
                text_highlighted = text

            output.append(f"[{start:6.1f}s - {end:6.1f}s] {text_highlighted}")

        output.append("-" * 80)

        return "\n".join(output)

    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            if self.temp_dir.exists():
                # Keep transcript cache, remove large audio files
                for audio_file in self.temp_dir.glob('*.mp3'):
                    audio_file.unlink()
                for audio_file in self.temp_dir.glob('*.m4a'):
                    audio_file.unlink()
        except Exception as e:
            print(f"Warning: Could not clean up temp files: {e}")


def main():
    """Main entry point for the skill."""
    extractor = PodcastTranscriptExtractor()

    try:
        # Step 1: Get feed URL
        print("Podcast Transcript Extraction Skill")
        print("=" * 80)
        feed_url = input("\nPodcast RSS Feed URL: ").strip()

        # Step 2: Fetch and display episodes
        feed = extractor.fetch_feed(feed_url)

        # Step 3: Select episode
        episode_query = input("\nEpisode title/number/date (or press Enter to see list): ").strip()
        entry, idx = extractor.select_episode(feed, episode_query if episode_query else None)

        # Step 4: Confirm selection
        if not extractor.confirm_selection(entry):
            print("Cancelled.")
            return

        # Step 5: Get audio URL
        audio_url = extractor.extract_audio_url(entry)
        if not audio_url:
            print("Error: No audio enclosure found for this episode")
            return

        # Step 6: Download audio
        audio_path = extractor.download_audio(audio_url, entry.get('title', 'episode'))

        # Step 7: Transcribe
        transcript = extractor.transcribe_audio(audio_path)

        # Step 8: Extract section
        print("\n" + "=" * 80)
        print("Extract transcript section")
        print("=" * 80)

        extraction_method = input("\nExtract by (t)imestamp or (c)ontext? [t/c]: ").strip().lower()

        if extraction_method == 't':
            start_str = input("Start time (MM:SS or HH:MM:SS): ").strip()
            end_str = input("End time (MM:SS or HH:MM:SS): ").strip()
            start_time = extractor.parse_timestamp(start_str)
            end_time = extractor.parse_timestamp(end_str)

            result = extractor.extract_by_timestamp(transcript, start_time, end_time, padding=30)
        else:
            context = input("What are you looking for (quote or topic)? ").strip()
            result = extractor.extract_by_context(transcript, context, padding=30)

        print("\n" + result)

        # Step 9: Offer to save
        save_choice = input("\nSave to file? (y/n): ").strip().lower()
        if save_choice in ('y', 'yes'):
            output_file = Path.cwd() / f"transcript_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(output_file, 'w') as f:
                f.write(result)
            print(f"Saved to: {output_file}")

        # Step 10: Cleanup
        extractor.cleanup()
        print("\nDone!")

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        extractor.cleanup()
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        extractor.cleanup()
        sys.exit(1)


if __name__ == '__main__':
    main()
