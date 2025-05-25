import os
import re
import requests
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from googleapiclient.discovery import build
from typing import List, Dict
import json

class YouTubeTopicSearcher:
    def __init__(self, youtube_api_key: str, cache_dir="/Data/tech_paris_hack"):
        self.youtube_api_key = youtube_api_key
        self.cache_dir = cache_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize YouTube API
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
        # Set up model caching
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["HF_HOME"] = cache_dir
        os.environ["TRANSFORMERS_CACHE"] = cache_dir

    def search_youtube_videos(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search YouTube for videos related to the query"""
        try:
            # Search for videos
            search_response = self.youtube.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=max_results,
                order='relevance',
                videoDuration='medium',  # Prefer medium length videos
                videoDefinition='any'
            ).execute()
            
            videos = []
            for item in search_response['items']:
                video_info = {
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'][:200] + "..." if len(item['snippet']['description']) > 200 else item['snippet']['description'],
                    'channel': item['snippet']['channelTitle'],
                    'published': item['snippet']['publishedAt'][:10],  # Date only
                    'video_id': item['id']['videoId'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    'thumbnail': item['snippet']['thumbnails']['medium']['url']
                }
                videos.append(video_info)
            
            return videos
            
        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return []

    def get_video_statistics(self, video_ids: List[str]) -> Dict:
        """Get statistics for videos (views, likes, duration)"""
        try:
            video_ids_str = ','.join(video_ids)
            stats_response = self.youtube.videos().list(
                part='statistics,contentDetails',
                id=video_ids_str
            ).execute()
            
            stats_dict = {}
            for item in stats_response['items']:
                video_id = item['id']
                stats_dict[video_id] = {
                    'views': item['statistics'].get('viewCount', 'N/A'),
                    'likes': item['statistics'].get('likeCount', 'N/A'),
                    'duration': item['contentDetails']['duration']
                }
            
            return stats_dict
            
        except Exception as e:
            print(f"Error getting video statistics: {e}")
            return {}

    def search_videos_for_topics(self, content: str, videos_per_topic: int = 3) -> Dict:
        """Complete workflow: extract topics and search for videos"""
        topics = ['derivatives and integrals']
        
        results = {}
        for topic in topics:
            print(f"Searching YouTube for: {topic}")
            
            search_query = f"{topic} tutorial explanation"
            videos = self.search_youtube_videos(search_query, videos_per_topic)
            
            if videos:
                video_ids = [v['video_id'] for v in videos]
                stats = self.get_video_statistics(video_ids)
                
                for video in videos:
                    video_id = video['video_id']
                    if video_id in stats:
                        video.update(stats[video_id])
                
                results[topic] = videos
                print(f" Found {len(videos)} videos for '{topic}'")
            else:
                print(f" No videos found for '{topic}'")
        
        return results

    def display_results(self, results: Dict):
        """Display search results in a formatted way"""
        if not results:
            print("No results to display")
            return
        
        print("\n" + "="*80)
        print("📺 YOUTUBE VIDEO RECOMMENDATIONS")
        print("="*80)
        
        for topic, videos in results.items():
            print(f"\n Topic: {topic.upper()}")
            print("-" * 60)
            
            for i, video in enumerate(videos, 1):
                print(f"\n{i}. {video['title']}")
                print(f"   Channel: {video['channel']}")
                print(f"   Published: {video['published']}")
                print(f"   Views: {video.get('views', 'N/A')}")
                print(f"   URL: {video['url']}")
                if video['description']:
                    print(f"   Description: {video['description']}")

    def save_results_to_json(self, results: Dict, filename: str = "youtube_recommendations.json"):
        """Save results to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving results: {e}")



if __name__ == "__main__":
    YOUTUBE_API_KEY = "AIzaSyC1EuvvSnzlRWKCTOcxRCWjyrKJ1bQnPrg"  

    searcher = YouTubeTopicSearcher(YOUTUBE_API_KEY)

    results = searcher.search_videos_for_topics(" ", videos_per_topic=3)

    searcher.display_results(results)
    
    searcher.save_results_to_json(results)