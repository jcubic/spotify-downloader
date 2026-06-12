"""
Download module for the console.
"""

import logging
from typing import List

from spotdl.download.downloader import Downloader
from spotdl.utils.search import get_simple_songs
from spotdl.utils.state_manager import StateManager

__all__ = ["download"]

logger = logging.getLogger(__name__)


def download(
    query: List[str],
    downloader: Downloader,
) -> None:
    """
    Find songs with the provided audio provider and save them to the disk.

    ### Arguments
    - query: list of strings to search for.
    """

    # Handle --state-info flag
    if downloader.settings.get("state_info"):
        display_state_info(query, downloader)
        return

    # Parse the query
    songs = get_simple_songs(
        query,
        use_ytm_data=downloader.settings["ytm_data"],
        playlist_numbering=downloader.settings["playlist_numbering"],
        albums_to_ignore=downloader.settings["ignore_albums"],
        album_type=downloader.settings["album_type"],
        playlist_retain_track_cover=downloader.settings["playlist_retain_track_cover"],
    )

    # Download the songs
    downloader.download_multiple_songs(songs)


def display_state_info(query: List[str], downloader: Downloader) -> None:
    """
    Display state information for a playlist/album.

    ### Arguments
    - query: list of strings to search for
    - downloader: Downloader instance
    """
    if not downloader.state_manager:
        logger.error("State tracking is disabled. Cannot show state info.")
        return

    # Parse the query to get the URL
    if not query or len(query) == 0:
        logger.error("Please provide a playlist or album URL")
        return

    url = query[0]
    list_info = StateManager.extract_list_info(url)

    if not list_info:
        logger.error("Invalid playlist/album URL")
        return

    list_type, list_id = list_info
    state_info = downloader.state_manager.get_state_info(list_type, list_id)

    if not state_info:
        logger.info("No state information found for this %s", list_type)
        return

    # Display state information
    print(f"\n{'='*60}")
    print(f"State Information for {state_info['type'].title()}")
    print(f"{'='*60}")
    print(f"Name: {state_info['name']}")
    print(f"URL: {state_info['url']}")
    print(f"Output Directory: {state_info['output_dir']}")
    print("\nProgress:")
    print(f"  Total Songs: {state_info['total']}")
    print(f"  Completed: {state_info['completed']}")
    print(f"  Failed: {state_info['failed']}")
    print(f"  Skipped: {state_info['skipped']}")
    print(f"  Pending: {state_info['pending']}")

    if state_info["total"] > 0:
        percent_complete = (state_info["completed"] / state_info["total"]) * 100
        print(f"  Progress: {percent_complete:.1f}%")

    print(f"\nLast Updated: {state_info.get('last_updated', 'N/A')}")
    print(f"Last Download: {state_info.get('last_download', 'N/A')}")
    print(f"{'='*60}\n")
