import os
import sys
from typing import List, Optional

import replicate
import requests
from moviepy.editor import VideoFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from mcp import FastMCP, tool

from auth_utils import get_authenticated_service, API_SERVICE_NAME, API_VERSION

class YouTubeMCP(FastMCP):
    def __init__(self):
        super().__init__("youtube_channel_manager")
        self.youtube = self._get_youtube_service()
        self.channel_id = self._get_channel_id()
        replicate.api_token = os.environ.get("REPLICATE_API_TOKEN")

    def _get_youtube_service(self):
        credentials = get_authenticated_service()
        return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    def _get_channel_id(self):
        try:
            response = self.youtube.channels().list(part="id", mine=True).execute()
            if response and response.get("items"):
                return response["items"][0]["id"]
            raise ValueError("Could not retrieve channel ID.")
        except HttpError as e:
            print(f"HTTP error {e.resp.status}: {e.content}")
            raise

    def get_channel_stats(self) -> dict:
        try:
            response = self.youtube.channels().list(part="statistics", id=self.channel_id).execute()
            if response and response.get("items"):
                stats = response["items"][0]["statistics"]
                return {"viewCount": stats.get("viewCount"), "subscriberCount": stats.get("subscriberCount"), "videoCount": stats.get("videoCount")}
            return {}
        except HttpError as e:
            print(f"HTTP error {e.resp.status}: {e.content}")
            raise

    def upload_video(self, file_path: str, title: str, description: str, tags: Optional[List[str]] = None, privacy_status: str = "private") -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found at: {file_path}")
        body = {"snippet": {"title": title, "description": description, "tags": tags, "categoryId": "22"}, "status": {"privacyStatus": privacy_status}}
        media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        try:
            request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media_body)
            response = request.execute()
            return {"videoId": response["id"], "title": response["snippet"]["title"], "privacyStatus": response["status"]["privacyStatus"]}
        except HttpError as e:
            print(f"HTTP error {e.resp.status}: {e.content}")
            raise

    def generate_video_clip(self, prompt: str, model: str = "minimax/video-01") -> str:
        if not replicate.api_token:
            raise EnvironmentError("REPLICATE_API_TOKEN is not set.")
        try:
            output = replicate.run(model, input={"prompt": prompt})
            video_url = output[0] if isinstance(output, list) else output
            if not video_url:
                raise ValueError("No video URL returned from Replicate.")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            file_name = f"generated_video_{abs(hash(prompt))}.mp4"
            with open(file_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return os.path.abspath(file_name)
        except Exception as e:
            print(f"Error generating video: {e}", file=sys.stderr)
            raise

    def compile_videos(self, video_paths: List[str], output_filename: str = "compiled_video.mp4") -> str:
        if not video_paths:
            raise ValueError("No video paths provided.")
        try:
            clips = [VideoFileClip(path) for path in video_paths]
            final_clip = concatenate_videoclips(clips)
            final_clip.write_videofile(output_filename, codec="libx264")
            for clip in clips:
                clip.close()
            return os.path.abspath(output_filename)
        except Exception as e:
            print(f"Error compiling videos: {e}", file=sys.stderr)
            raise

    def create_funny_animal_video(self, prompts: List[str], title: str, description: str, tags: Optional[List[str]] = None, privacy_status: str = "private") -> dict:
        if not prompts:
            raise ValueError("No prompts provided.")
        generated_video_paths = []
        try:
            for prompt in prompts:
                generated_video_paths.append(self.generate_video_clip(prompt))
            compiled_video_path = self.compile_videos(generated_video_paths) if len(generated_video_paths) > 1 else generated_video_paths[0]
            upload_result = self.upload_video(file_path=compiled_video_path, title=title, description=description, tags=tags, privacy_status=privacy_status)
            return upload_result
        except Exception as e:
            print(f"Error creating video: {e}", file=sys.stderr)
            raise
        finally:
            for path in generated_video_paths:
                if os.path.exists(path):
                    os.remove(path)

if __name__ == "__main__":
    try:
        mcp_server = YouTubeMCP()
        mcp_server.run()
    except Exception as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)
