"""
State manager for tracking download progress.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from spotdl.types.song import Song
from spotdl.utils.state import (
    PlaylistState,
    SongState,
    SongStatus,
    get_iso_timestamp,
    compute_settings_hash,
    compute_file_hash,
)

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages download state for playlists and albums.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize state manager.
        
        Args:
            state_dir: Directory to store state files. If None, uses ./.spotdl
        """
        self.state_dir = state_dir or Path.cwd() / ".spotdl"
        self.playlists_dir = self.state_dir / "playlists"
        self.albums_dir = self.state_dir / "albums"

        # Create directories if they don't exist
        self.playlists_dir.mkdir(parents=True, exist_ok=True)
        self.albums_dir.mkdir(parents=True, exist_ok=True)

    def get_list_dir(self, list_type: str, list_id: str) -> Path:
        """
        Get directory for a playlist or album.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            
        Returns:
            Path to list directory
        """
        base_dir = self.playlists_dir if list_type == "playlist" else self.albums_dir
        list_dir = base_dir / list_id
        list_dir.mkdir(parents=True, exist_ok=True)
        return list_dir

    def load_playlist_state(self, list_type: str, list_id: str) -> Optional[PlaylistState]:
        """
        Load playlist or album state.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            
        Returns:
            PlaylistState if exists, None otherwise
        """
        list_dir = self.get_list_dir(list_type, list_id)
        metadata_file = list_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PlaylistState.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load state from {metadata_file}: {e}")
            return None

    def save_playlist_state(self, state: PlaylistState) -> None:
        """
        Save playlist or album state.
        
        Args:
            state: PlaylistState to save
        """
        list_dir = self.get_list_dir(state.type, state.id)
        metadata_file = list_dir / "metadata.json"

        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state to {metadata_file}: {e}")

    def load_song_state(self, list_type: str, list_id: str, song_id: str) -> Optional[SongState]:
        """
        Load song state.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            song_id: Spotify song ID
            
        Returns:
            SongState if exists, None otherwise
        """
        list_dir = self.get_list_dir(list_type, list_id)
        songs_dir = list_dir / "songs"
        song_file = songs_dir / f"{song_id}.json"

        if not song_file.exists():
            return None

        try:
            with open(song_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SongState.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load song state from {song_file}: {e}")
            return None

    def save_song_state(self, list_type: str, list_id: str, state: SongState) -> None:
        """
        Save song state.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            state: SongState to save
        """
        list_dir = self.get_list_dir(list_type, list_id)
        songs_dir = list_dir / "songs"
        songs_dir.mkdir(exist_ok=True)
        song_file = songs_dir / f"{state.id}.json"

        try:
            with open(song_file, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save song state to {song_file}: {e}")

    def load_all_song_states(self, list_type: str, list_id: str) -> Dict[str, SongState]:
        """
        Load all song states for a playlist/album.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            
        Returns:
            Dictionary mapping song_id to SongState
        """
        list_dir = self.get_list_dir(list_type, list_id)
        songs_dir = list_dir / "songs"

        if not songs_dir.exists():
            return {}

        states = {}
        for song_file in songs_dir.glob("*.json"):
            song_id = song_file.stem
            state = self.load_song_state(list_type, list_id, song_id)
            if state:
                states[song_id] = state

        return states

    def update_song_status(
        self,
        list_type: str,
        list_id: str,
        song_id: str,
        status: SongStatus,
        **kwargs: Any,
    ) -> None:
        """
        Update song status and other fields.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            song_id: Spotify song ID
            status: New status
            **kwargs: Additional fields to update
        """
        state = self.load_song_state(list_type, list_id, song_id)
        if not state:
            logger.warning(f"Cannot update status for non-existent song {song_id}")
            return

        state.status = status
        state.last_attempt = get_iso_timestamp()

        if status == SongStatus.COMPLETED:
            state.completed_at = get_iso_timestamp()

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        self.save_song_state(list_type, list_id, state)

    def get_pending_songs(self, list_type: str, list_id: str) -> List[SongState]:
        """
        Get all pending songs.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            
        Returns:
            List of pending SongStates
        """
        states = self.load_all_song_states(list_type, list_id)
        return [s for s in states.values() if s.status == SongStatus.PENDING]

    def get_failed_songs(self, list_type: str, list_id: str) -> List[SongState]:
        """
        Get all failed songs.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            
        Returns:
            List of failed SongStates
        """
        states = self.load_all_song_states(list_type, list_id)
        return [s for s in states.values() if s.status == SongStatus.FAILED]

    def cleanup_state(self, list_type: str, list_id: str) -> None:
        """
        Remove state directory for a playlist/album.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
        """
        list_dir = self.get_list_dir(list_type, list_id)
        try:
            import shutil

            shutil.rmtree(list_dir)
            logger.info(f"Cleaned up state directory: {list_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup state directory {list_dir}: {e}")

    def initialize_from_songs(
        self,
        songs: List[Song],
        list_type: str,
        list_id: str,
        list_url: str,
        list_name: str,
        output_dir: str,
        settings: Dict[str, Any],
        snapshot_id: Optional[str] = None,
    ) -> PlaylistState:
        """
        Initialize state from a list of songs.
        
        Args:
            songs: List of Song objects
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            list_url: Spotify URL
            list_name: Playlist/album name
            output_dir: Output directory
            settings: Download settings
            snapshot_id: Spotify playlist snapshot ID
            
        Returns:
            Initialized PlaylistState
        """
        # Create or load playlist state
        playlist_state = self.load_playlist_state(list_type, list_id)

        if playlist_state:
            # Update existing state
            playlist_state.total_tracks = len(songs)
            playlist_state.last_updated = get_iso_timestamp()
            playlist_state.settings_hash = compute_settings_hash(settings)
            if snapshot_id:
                playlist_state.snapshot_id = snapshot_id
        else:
            # Create new state
            playlist_state = PlaylistState(
                id=list_id,
                url=list_url,
                name=list_name,
                type=list_type,
                total_tracks=len(songs),
                last_updated=get_iso_timestamp(),
                snapshot_id=snapshot_id,
                output_dir=output_dir,
                settings_hash=compute_settings_hash(settings),
            )

        # Load existing song states
        existing_states = self.load_all_song_states(list_type, list_id)

        # Initialize song states
        for song in songs:
            song_id = song.song_id

            if song_id in existing_states:
                # Keep existing state
                continue

            # Create new song state
            song_state = SongState(
                id=song_id,
                url=song.url,
                name=song.name,
                artists=song.artists,
                status=SongStatus.PENDING,
                metadata=song.json,
            )
            self.save_song_state(list_type, list_id, song_state)

        # Update counts
        all_states = self.load_all_song_states(list_type, list_id)
        playlist_state.update_counts(list(all_states.values()))

        # Save playlist state
        self.save_playlist_state(playlist_state)

        return playlist_state

    def get_state_info(self, list_type: str, list_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary information about download state.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            
        Returns:
            Dictionary with state information or None if no state exists
        """
        playlist_state = self.load_playlist_state(list_type, list_id)
        if not playlist_state:
            return None

        all_states = self.load_all_song_states(list_type, list_id)
        playlist_state.update_counts(list(all_states.values()))

        return {
            "name": playlist_state.name,
            "type": playlist_state.type,
            "url": playlist_state.url,
            "total": playlist_state.total_tracks,
            "completed": playlist_state.downloaded,
            "failed": playlist_state.failed,
            "skipped": playlist_state.skipped,
            "pending": playlist_state.pending,
            "last_updated": playlist_state.last_updated,
            "last_download": playlist_state.last_download,
            "output_dir": playlist_state.output_dir,
        }

    def verify_completed_files(
        self, list_type: str, list_id: str, output_dir: Path
    ) -> List[str]:
        """
        Verify that completed files still exist.
        
        Args:
            list_type: "playlist" or "album"
            list_id: Spotify playlist/album ID
            output_dir: Output directory to check
            
        Returns:
            List of song IDs with missing files
        """
        all_states = self.load_all_song_states(list_type, list_id)
        missing = []

        for song_id, state in all_states.items():
            if state.status == SongStatus.COMPLETED and state.output_path:
                file_path = output_dir / state.output_path
                if not file_path.exists():
                    missing.append(song_id)
                    # Reset to pending
                    state.status = SongStatus.PENDING
                    state.output_path = None
                    state.completed_at = None
                    self.save_song_state(list_type, list_id, state)

        return missing

    @staticmethod
    def extract_list_info(url: str) -> Optional[tuple[str, str]]:
        """
        Extract list type and ID from Spotify URL.
        
        Args:
            url: Spotify URL
            
        Returns:
            Tuple of (list_type, list_id) or None if not a valid playlist/album URL
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) >= 2:
                list_type = path_parts[0]
                list_id = path_parts[1].split("?")[0]  # Remove query params

                if list_type in ["playlist", "album"]:
                    return list_type, list_id
        except Exception:
            pass

        return None
