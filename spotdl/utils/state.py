"""
State management data models for tracking download progress.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class SongStatus(str, Enum):
    """Status of a song download."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SongState:
    """
    State information for a single song download.
    """

    id: str  # Spotify song ID
    url: str  # Spotify URL
    name: str  # Song name
    artists: List[str]  # Artist names
    status: SongStatus = SongStatus.PENDING
    output_path: Optional[str] = None  # Path to downloaded file (relative to output dir)
    download_url: Optional[str] = None  # Resolved audio source URL
    error: Optional[str] = None  # Error message if failed
    attempts: int = 0  # Number of download attempts
    last_attempt: Optional[str] = None  # ISO timestamp of last attempt
    completed_at: Optional[str] = None  # ISO timestamp when completed
    file_hash: Optional[str] = None  # Hash of downloaded file for integrity
    metadata: Dict[str, Any] = field(default_factory=dict)  # Full Song metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SongState":
        """Create from dictionary loaded from JSON."""
        data = data.copy()
        if "status" in data:
            data["status"] = SongStatus(data["status"])
        return cls(**data)


@dataclass
class PlaylistState:
    """
    State information for a playlist or album download.
    """

    id: str  # Spotify playlist/album ID
    url: str  # Full Spotify URL
    name: str  # Playlist/album name
    type: str  # "playlist" or "album"
    total_tracks: int  # Total number of tracks
    downloaded: int = 0  # Successfully downloaded count
    failed: int = 0  # Failed download count
    skipped: int = 0  # Skipped (already exists) count
    pending: int = 0  # Pending download count
    last_updated: Optional[str] = None  # ISO timestamp of last Spotify fetch
    last_download: Optional[str] = None  # ISO timestamp of last download attempt
    snapshot_id: Optional[str] = None  # Spotify playlist snapshot ID
    output_dir: str = ""  # Output directory used
    settings_hash: str = ""  # Hash of relevant download settings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaylistState":
        """Create from dictionary loaded from JSON."""
        return cls(**data)

    def update_counts(self, songs: List[SongState]) -> None:
        """Update counts based on song states."""
        self.downloaded = sum(1 for s in songs if s.status == SongStatus.COMPLETED)
        self.failed = sum(1 for s in songs if s.status == SongStatus.FAILED)
        self.skipped = sum(1 for s in songs if s.status == SongStatus.SKIPPED)
        self.pending = sum(1 for s in songs if s.status == SongStatus.PENDING)


def get_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def compute_settings_hash(settings: Dict[str, Any]) -> str:
    """
    Compute a hash of relevant download settings to detect changes.
    
    Args:
        settings: Dictionary of settings
        
    Returns:
        Hash string
    """
    import hashlib
    import json

    # Select only settings that affect output
    relevant_keys = [
        "format",
        "bitrate",
        "audio_provider",
        "lyrics_provider",
        "generate_lrc",
        "output",
    ]

    relevant_settings = {k: settings.get(k) for k in relevant_keys if k in settings}
    settings_json = json.dumps(relevant_settings, sort_keys=True)
    return hashlib.md5(settings_json.encode()).hexdigest()


def compute_file_hash(file_path: str) -> str:
    """
    Compute MD5 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash string
    """
    import hashlib

    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""
