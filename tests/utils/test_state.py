"""
Tests for state management functionality.
"""

import pytest
from pathlib import Path

from spotdl.utils.state import (
    SongState,
    SongStatus,
    PlaylistState,
    get_iso_timestamp,
    compute_settings_hash,
)
from spotdl.utils.state_manager import StateManager


def test_song_state_creation():
    """Test creating a SongState."""
    state = SongState(
        id="test_id",
        url="https://open.spotify.com/track/test_id",
        name="Test Song",
        artists=["Test Artist"],
        status=SongStatus.PENDING,
    )

    assert state.id == "test_id"
    assert state.status == SongStatus.PENDING
    assert state.attempts == 0


def test_song_state_serialization():
    """Test SongState serialization/deserialization."""
    state = SongState(
        id="test_id",
        url="https://open.spotify.com/track/test_id",
        name="Test Song",
        artists=["Test Artist"],
        status=SongStatus.COMPLETED,
        output_path="Test Artist - Test Song.mp3",
    )

    # Serialize
    data = state.to_dict()
    assert data["id"] == "test_id"
    assert data["status"] == "completed"

    # Deserialize
    restored = SongState.from_dict(data)
    assert restored.id == state.id
    assert restored.status == state.status
    assert restored.output_path == state.output_path


def test_playlist_state_creation():
    """Test creating a PlaylistState."""
    state = PlaylistState(
        id="playlist_id",
        url="https://open.spotify.com/playlist/playlist_id",
        name="Test Playlist",
        type="playlist",
        total_tracks=10,
        output_dir="/output",
        settings_hash="abc123",
    )

    assert state.id == "playlist_id"
    assert state.type == "playlist"
    assert state.total_tracks == 10


def test_playlist_state_update_counts():
    """Test updating playlist counts based on song states."""
    playlist_state = PlaylistState(
        id="playlist_id",
        url="https://open.spotify.com/playlist/playlist_id",
        name="Test Playlist",
        type="playlist",
        total_tracks=5,
        output_dir="/output",
        settings_hash="abc123",
    )

    songs = [
        SongState(
            id="1",
            url="url1",
            name="Song 1",
            artists=["Artist"],
            status=SongStatus.COMPLETED,
        ),
        SongState(
            id="2",
            url="url2",
            name="Song 2",
            artists=["Artist"],
            status=SongStatus.COMPLETED,
        ),
        SongState(
            id="3",
            url="url3",
            name="Song 3",
            artists=["Artist"],
            status=SongStatus.FAILED,
        ),
        SongState(
            id="4",
            url="url4",
            name="Song 4",
            artists=["Artist"],
            status=SongStatus.PENDING,
        ),
        SongState(
            id="5",
            url="url5",
            name="Song 5",
            artists=["Artist"],
            status=SongStatus.SKIPPED,
        ),
    ]

    playlist_state.update_counts(songs)

    assert playlist_state.downloaded == 2
    assert playlist_state.failed == 1
    assert playlist_state.pending == 1
    assert playlist_state.skipped == 1


def test_state_manager_initialization(tmpdir):
    """Test StateManager initialization."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    assert manager.state_dir == state_dir
    assert manager.playlists_dir.exists()
    assert manager.albums_dir.exists()


def test_state_manager_save_load_playlist(tmpdir):
    """Test saving and loading playlist state."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    # Create and save playlist state
    playlist_state = PlaylistState(
        id="test_playlist",
        url="https://open.spotify.com/playlist/test_playlist",
        name="Test Playlist",
        type="playlist",
        total_tracks=5,
        output_dir="/output",
        settings_hash="abc123",
    )

    manager.save_playlist_state(playlist_state)

    # Load playlist state
    loaded_state = manager.load_playlist_state("playlist", "test_playlist")

    assert loaded_state is not None
    assert loaded_state.id == "test_playlist"
    assert loaded_state.name == "Test Playlist"
    assert loaded_state.total_tracks == 5


def test_state_manager_save_load_song(tmpdir):
    """Test saving and loading song state."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    # Create and save song state
    song_state = SongState(
        id="test_song",
        url="https://open.spotify.com/track/test_song",
        name="Test Song",
        artists=["Test Artist"],
        status=SongStatus.PENDING,
    )

    manager.save_song_state("playlist", "test_playlist", song_state)

    # Load song state
    loaded_state = manager.load_song_state("playlist", "test_playlist", "test_song")

    assert loaded_state is not None
    assert loaded_state.id == "test_song"
    assert loaded_state.name == "Test Song"
    assert loaded_state.status == SongStatus.PENDING


def test_state_manager_update_song_status(tmpdir):
    """Test updating song status."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    # Create initial song state
    song_state = SongState(
        id="test_song",
        url="https://open.spotify.com/track/test_song",
        name="Test Song",
        artists=["Test Artist"],
        status=SongStatus.PENDING,
    )

    manager.save_song_state("playlist", "test_playlist", song_state)

    # Update status
    manager.update_song_status(
        "playlist",
        "test_playlist",
        "test_song",
        SongStatus.COMPLETED,
        output_path="output/song.mp3",
    )

    # Load and verify
    updated_state = manager.load_song_state("playlist", "test_playlist", "test_song")

    assert updated_state is not None
    assert updated_state.status == SongStatus.COMPLETED
    assert updated_state.output_path == "output/song.mp3"


def test_state_manager_load_all_songs(tmpdir):
    """Test loading all song states."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    # Create multiple song states
    for i in range(3):
        song_state = SongState(
            id=f"song_{i}",
            url=f"https://open.spotify.com/track/song_{i}",
            name=f"Song {i}",
            artists=["Test Artist"],
            status=SongStatus.PENDING,
        )
        manager.save_song_state("playlist", "test_playlist", song_state)

    # Load all
    all_states = manager.load_all_song_states("playlist", "test_playlist")

    assert len(all_states) == 3
    assert "song_0" in all_states
    assert "song_1" in all_states
    assert "song_2" in all_states


def test_state_manager_get_pending_songs(tmpdir):
    """Test getting pending songs."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    # Create mixed states
    states = [
        (SongStatus.PENDING, "song_0"),
        (SongStatus.COMPLETED, "song_1"),
        (SongStatus.PENDING, "song_2"),
    ]

    for status, song_id in states:
        song_state = SongState(
            id=song_id,
            url=f"https://open.spotify.com/track/{song_id}",
            name=f"Song {song_id}",
            artists=["Test Artist"],
            status=status,
        )
        manager.save_song_state("playlist", "test_playlist", song_state)

    # Get pending
    pending = manager.get_pending_songs("playlist", "test_playlist")

    assert len(pending) == 2
    assert all(s.status == SongStatus.PENDING for s in pending)


def test_state_manager_get_failed_songs(tmpdir):
    """Test getting failed songs."""
    state_dir = Path(tmpdir) / "test_state"
    manager = StateManager(state_dir)

    # Create mixed states
    states = [
        (SongStatus.FAILED, "song_0"),
        (SongStatus.COMPLETED, "song_1"),
        (SongStatus.FAILED, "song_2"),
    ]

    for status, song_id in states:
        song_state = SongState(
            id=song_id,
            url=f"https://open.spotify.com/track/{song_id}",
            name=f"Song {song_id}",
            artists=["Test Artist"],
            status=status,
        )
        manager.save_song_state("playlist", "test_playlist", song_state)

    # Get failed
    failed = manager.get_failed_songs("playlist", "test_playlist")

    assert len(failed) == 2
    assert all(s.status == SongStatus.FAILED for s in failed)


def test_state_manager_extract_list_info():
    """Test extracting list info from URL."""
    # Playlist URL
    playlist_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    result = StateManager.extract_list_info(playlist_url)
    assert result is not None
    assert result[0] == "playlist"
    assert result[1] == "37i9dQZF1DXcBWIGoYBM5M"

    # Album URL
    album_url = "https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy"
    result = StateManager.extract_list_info(album_url)
    assert result is not None
    assert result[0] == "album"
    assert result[1] == "4aawyAB9vmqN3uQ7FjRGTy"

    # Invalid URL
    invalid_url = "https://open.spotify.com/track/invalid"
    result = StateManager.extract_list_info(invalid_url)
    assert result is None


def test_compute_settings_hash():
    """Test computing settings hash."""
    settings1 = {"format": "mp3", "bitrate": "320k", "other": "value"}
    settings2 = {"format": "mp3", "bitrate": "320k", "other": "different"}
    settings3 = {"format": "flac", "bitrate": "320k", "other": "value"}

    hash1 = compute_settings_hash(settings1)
    hash2 = compute_settings_hash(settings2)
    hash3 = compute_settings_hash(settings3)

    # Same relevant settings should produce same hash
    assert hash1 == hash2

    # Different relevant settings should produce different hash
    assert hash1 != hash3


def test_get_iso_timestamp():
    """Test getting ISO timestamp."""
    timestamp = get_iso_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) > 0
    # Basic ISO format check
    assert "T" in timestamp
