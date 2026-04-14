# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 22:17:15 2026

@author: yongr
"""

import re
import json

class NarrationToStoryboard:
    def __init__(self, file_path):
        self.file_path = file_path
        self.production_name = "鸦片战争"
        self.scenes = []

    def parse(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match each scene block starting with "## 场次XX"
        scene_blocks = re.findall(r'## 场次\d+(.*?)(?=## 场次|$)', content, re.DOTALL)

        for idx, block in enumerate(scene_blocks, 1):
            # 1. Extract narration text: ignore blockquotes (>) and headers (#)
            lines = block.split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('>'):
                    continue
                clean_lines.append(line)
            
            full_text = "".join(clean_lines)

            # 2. Split logic: use regex to split by Chinese punctuation
            # We keep the punctuation in 'parts' to know where the breaks are
            parts = re.split(r'([。！？；，])', full_text)
            
            scripts = []
            temp_sentence = ""
            
            # Reassemble text segments
            for i in range(0, len(parts) - 1, 2):
                text = parts[i].strip()
                # punc = parts[i+1] # We identify the break here but won't append it to the final string
                
                if not text:
                    continue
                
                # Combine current segment with buffer
                if temp_sentence:
                    temp_sentence += text
                else:
                    temp_sentence = text
                
                # Length constraint: Check if current buffer (without trailing punc) >= 5
                if len(temp_sentence) >= 5:
                    scripts.append({
                        "No": len(scripts) + 1,
                        "Sentence": temp_sentence
                    })
                    temp_sentence = "" # Reset buffer
            
            # Handle remaining fragments
            if temp_sentence:
                # Remove any stray punctuation that might have slipped into the end of text
                temp_sentence = re.sub(r'[。！？；，]$', '', temp_sentence.strip())
                if temp_sentence:
                    if scripts:
                        # Append to last sentence if still too short, or keep as a new one
                        scripts[-1]["Sentence"] += temp_sentence
                    else:
                        scripts.append({
                            "No": 1,
                            "Sentence": temp_sentence
                        })

            if scripts:
                self.scenes.append({
                    "ID": idx,
                    "Frame": f"../frames/{str(idx).zfill(3)}.png",
                    "Scripts": scripts
                })

    def save_to_json(self, output_path):
        data = {
            "Production": self.production_name,
            "Scenes": self.scenes
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Conversion successful! Saved {len(self.scenes)} scenes to: {output_path}")

if __name__ == "__main__":
    # Ensure narration.md is in the same directory
    converter = NarrationToStoryboard('../story/narration.md')
    converter.parse()
    converter.save_to_json('../story/storyboard.json')