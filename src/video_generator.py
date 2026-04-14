# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 15:37:34 2026

@author: yongr
"""

# -*- coding: utf-8 -*-
import asyncio
import json
import edge_tts
import nest_asyncio
import os
import re
import sys  # Required for exiting the program
import time # Required for sleep between retries
from moviepy import TextClip, ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, CompositeAudioClip

nest_asyncio.apply()

class VideoGenerator:
    def __init__(self, default_voice="zh-CN-YunxiNeural", fps=24):
        self.default_voice = default_voice
        self.fps = fps

    async def _generate_audio(self, text, audio_path, voice=None):
        # Clean text to ensure there's actual content for TTS
        content_check = re.sub(r'[^\w\u4e00-\u9fa5]', '', text)
        if not content_check:
            return False

        try:
            communicate = edge_tts.Communicate(text, voice or self.default_voice)
            await communicate.save(audio_path)
            return True
        except Exception as e:
            print(f"  [Error] TTS failed for '{text[:10]}...': {e}")
            return False

    def zoom_in_effect(self, clip, zoom_speed=0.01):
        """Apply a continuous zoom-in effect to the clip."""
        return clip.resized(lambda t: 1 + zoom_speed * t)

    def create_video(self, json_path, output_path, size=(1920, 1080)):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_scene_clips = []
        if not os.path.exists("../story/temp_audio"):
            os.makedirs("../story/temp_audio")

        for scene in data["Scenes"]:
            scene_id = scene["ID"]
            frame_img_path = scene["Frame"]
            
            if not os.path.exists(frame_img_path):
                print(f"Warning: Image not found {frame_img_path}. Skipping Scene {scene_id}.")
                continue

            current_scene_text_clips = []
            current_scene_audio_clips = []
            total_scene_duration = 0

            # Step 1: Process each sentence in the scene
            for script in scene["Scripts"]:
                sentence_text = script["Sentence"].strip()
                # Append a period for better TTS rhythm
                full_tts_text = sentence_text + "。" 
                sentence_no = script["No"]
                audio_filename = f"audio_s{scene_id}_n{sentence_no}.mp3"
                temp_audio_path = os.path.join("../story/temp_audio", audio_filename)

                # --- Retry Logic for TTS ---
                success = False
                max_retries = 10
                for attempt in range(1, max_retries + 1):
                    print(f"  [Audio] Attempt {attempt}/{max_retries}: Generating for Scene {scene_id}, Sentence {sentence_no}...")
                    
                    success = asyncio.run(self._generate_audio(full_tts_text, temp_audio_path))
                    
                    if success:
                        break
                    elif attempt < max_retries:
                        print("  [Retry] TTS failed. Retrying in 2 seconds...")
                        time.sleep(2) # Wait briefly before next attempt
                
                if not success:
                    print(f"\n[CRITICAL ERROR] TTS failed after {max_retries} attempts for Scene {scene_id}.")
                    print("Exiting video generation program.")
                    sys.exit(1) # Terminate the process
                # ---------------------------

                # If successful, proceed with clip creation
                audio_clip = AudioFileClip(temp_audio_path)
                
                # Create TextClip (Subtitle)
                text_clip = (TextClip(
                                text=sentence_text, 
                                font_size=int(60), 
                                color='white', 
                                stroke_color='black',
                                stroke_width=int(2),
                                size=(int(size[0]*0.8), None), 
                                method='caption',
                                font=r'C:\Windows\Fonts\simkai.ttf' 
                            )
                            .with_duration(audio_clip.duration)
                            .with_start(total_scene_duration) # Start after previous sentences
                            .with_position(('center', int(size[1] * 0.85))))

                # Sequence audio with start time
                audio_with_timing = audio_clip.with_start(total_scene_duration)
                
                current_scene_text_clips.append(text_clip)
                current_scene_audio_clips.append(audio_with_timing)
                
                total_scene_duration += audio_clip.duration

            # Step 2: Create background for the scene
            if total_scene_duration > 0:
                bg_clip = (ImageClip(frame_img_path)
                           .with_duration(total_scene_duration)
                           .resized(height=size[1]))
                
                # Apply zoom effect
                bg_zoomed = self.zoom_in_effect(bg_clip).with_position('center')

                # Step 3: Combine Background + Subtitles + Audios
                scene_video = CompositeVideoClip([bg_zoomed] + current_scene_text_clips, size=size)
                scene_video.audio = CompositeAudioClip(current_scene_audio_clips)

                all_scene_clips.append(scene_video)
                print(f"[*] Scene {scene_id} completed. Total duration: {total_scene_duration:.2f}s")

        # Step 4: Final Assembly
        if not all_scene_clips:
            print("No clips were generated. Please check your data.")
            return

        print("\nConcatenating all scenes into final video...")
        final_video = concatenate_videoclips(all_scene_clips, method="compose")
        final_video.write_videofile(output_path, fps=self.fps, codec="libx264", audio_codec="aac")
        
        # Cleanup
        for clip in all_scene_clips:
            clip.close()

if __name__ == "__main__":
    generator = VideoGenerator()
    # Ensure paths match your directory structure
    generator.create_video(
        json_path="../story/storyboard.json", 
        output_path="../story/movie.mp4"
    )
