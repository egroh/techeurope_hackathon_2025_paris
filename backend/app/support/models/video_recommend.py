# app/support/models/video_recommend.py
import logging
from typing import List, Dict, Any
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# --- WARNING: HARDCODED API KEY - NOT FOR PRODUCTION ---
# Replace with your actual key for testing, but be aware of the risks.
YOUTUBE_API_KEY_HARDCODED = "AIzaSyC1EuvvSnzlRWKCTOcxRCWjyrKJ1bQnPrg"
# --- END WARNING ---

class YouTubeTopicSearcher:
    def __init__(self):
        self.youtube_api_key = YOUTUBE_API_KEY_HARDCODED
        try:
            self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            logger.info("YouTubeTopicSearcher initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube client: {e}")
            self.youtube = None


    def search_youtube_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.youtube:
            logger.error("YouTube client not initialized. Cannot search videos.")
            return []
        try:
            search_response = self.youtube.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=max_results,
                order='relevance',
                videoDuration='medium',
                videoDefinition='any'
            ).execute()

            videos = []
            for item in search_response.get('items', []):
                snippet = item.get('snippet', {})
                video_info = {
                    'title': snippet.get('title'),
                    'description': snippet.get('description', '')[:200] + "..." if len(snippet.get('description', '')) > 200 else snippet.get('description', ''),
                    'channel': snippet.get('channelTitle'),
                    'published_at': snippet.get('publishedAt', '')[:10],
                    'video_id': item.get('id', {}).get('videoId'),
                    'url': f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId')}" if item.get('id', {}).get('videoId') else None,
                    'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url')
                }
                if video_info['video_id']: # Only add if video_id is present
                    videos.append(video_info)
            return videos
        except HttpError as e:
            logger.error(f"YouTube API search error (HttpError) for query '{query}': {e.resp.status} {e._get_reason()}")
            error_content = json.loads(e.content).get('error', {})
            logger.error(f"Error details: {error_content.get('message')}")
            for err in error_content.get('errors', []):
                logger.error(f"  Reason: {err.get('reason')}, Message: {err.get('message')}")
            return []
        except Exception as e:
            logger.error(f"Error searching YouTube for query '{query}': {e}", exc_info=True)
            return []

    def get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not self.youtube or not video_ids:
            logger.error("YouTube client not initialized or no video IDs provided.")
            return {}
        try:
            video_ids_str = ','.join(video_ids)
            stats_response = self.youtube.videos().list(
                part='statistics,contentDetails',
                id=video_ids_str
            ).execute()

            stats_dict = {}
            for item in stats_response.get('items', []):
                video_id = item['id']
                stats = item.get('statistics', {})
                content_details = item.get('contentDetails', {})
                stats_dict[video_id] = {
                    'views': stats.get('viewCount'),
                    'likes': stats.get('likeCount'),
                    'duration': content_details.get('duration')
                }
            return stats_dict
        except HttpError as e:
            logger.error(f"YouTube API statistics error (HttpError) for video_ids: {e.resp.status} {e._get_reason()}")
            # Log more details if needed
            return {}
        except Exception as e:
            logger.error(f"Error getting video statistics: {e}", exc_info=True)
            return {}

    def search_videos_for_topics(
        self,
        topics: List[str], # Changed from content: str to topics: List[str]
        videos_per_topic: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not self.youtube:
            logger.error("YouTube client not initialized. Cannot search by topics.")
            return {}

        # For this example, we'll directly use the provided topics.
        # In a more advanced scenario, you'd extract topics from a larger text content.
        if not topics:
            logger.warning("No topics provided for YouTube search.")
            return {}

        results: Dict[str, List[Dict[str, Any]]] = {}
        for topic in topics:
            logger.info(f"Searching YouTube for topic: {topic}")
            search_query = f"{topic} tutorial explanation" # You can refine this query logic
            videos = self.search_youtube_videos(search_query, videos_per_topic)

            if videos:
                video_ids = [v['video_id'] for v in videos if v['video_id']]
                if video_ids:
                    stats = self.get_video_statistics(video_ids)
                    for video in videos:
                        video_id = video.get('video_id')
                        if video_id and video_id in stats:
                            video.update(stats[video_id])
                results[topic] = videos
                logger.info(f"Found {len(videos)} videos for '{topic}'")
            else:
                logger.info(f"No videos found for '{topic}'")
        return results

# youtube_searcher_service = YouTubeTopicSearcher()
