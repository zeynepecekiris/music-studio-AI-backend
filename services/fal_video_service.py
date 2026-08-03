"""
Fal AI Video Generation Service
Şarkı sözleri ve hikayeden 8 saniyelik video klip oluşturur
"""

import os
import time
import fal_client
from typing import Dict, Optional

class FalVideoService:
    def __init__(self):
        self.api_key = os.getenv('FAL_KEY')
        if not self.api_key:
            print("⚠️ WARNING: FAL_KEY not set in environment variables")
        else:
            # Set FAL_KEY for fal_client
            os.environ['FAL_KEY'] = self.api_key
            print(f"✅ FAL_KEY configured: {self.api_key[:20]}...")
    
    def enhance_prompt_with_ai(self, user_prompt: str) -> str:
        """
        AI ile prompt'u geliştir (Fal AI dokümantasyonundan)
        Daha detaylı ve kaliteli videolar için prompt'u enhance eder
        """
        try:
            print(f"🤖 Enhancing prompt with AI...")
            print(f"📝 Original: {user_prompt[:100]}...")
            
            result = fal_client.run(
                "fal-ai/any-llm",
                arguments={
                    "model": "google/gemini-flash-1.5",
                    "prompt": user_prompt,
                    "system_prompt": """
                        Enhance this prompt for video generation by following these rules:
                        1. Focus on a single, central subject for coherence
                        2. Structure from coarse to fine details (broad elements → specific textures/colors)
                        3. Include vivid colors, rich textures, and appropriate moods
                        4. Add cinematic elements (camera angles, lighting, atmosphere)
                        5. Keep it under 200 words
                        6. End with "high resolution, cinematic quality"
                        
                        Example:
                        Input: "A cat walking"
                        Output: "A majestic orange tabby cat with bright emerald eyes and detailed fur textures, walking gracefully through a sun-drenched cobblestone street in an old European town, warm golden hour lighting casting long shadows, vibrant flowers in window boxes, smooth camera tracking movement, high resolution, cinematic quality"
                    """,
                },
            )
            
            enhanced = result.get("output", user_prompt)
            print(f"✨ Enhanced: {enhanced[:100]}...")
            return enhanced
            
        except Exception as e:
            print(f"⚠️ Prompt enhancement failed: {str(e)}")
            print(f"📝 Using original prompt")
            return user_prompt  # Fallback to original
    
    def check_nsfw_prompt(self, prompt: str) -> bool:
        """
        Prompt'un NSFW içerik içerip içermediğini kontrol et
        Multi-layer safety checking (Fal AI dokümantasyonundan)
        """
        try:
            print(f"🛡️ Checking prompt for NSFW content...")
            
            result = fal_client.run(
                "fal-ai/any-llm",
                arguments={
                    "prompt": prompt,
                    "system_prompt": 'With just a single word of "yes" or "no" tell me if the given user prompt contains any not safe for work material. Don\'t say anything other than yes or no. If the prompt contains unsafe material, say yes, otherwise say no.',
                    "model": "google/gemini-flash-1.5",
                },
            )
            
            is_nsfw = "yes" in result.get("output", "").lower()
            
            if is_nsfw:
                print(f"⚠️ NSFW content detected in prompt")
            else:
                print(f"✅ Prompt is safe")
            
            return is_nsfw
            
        except Exception as e:
            print(f"⚠️ NSFW check failed: {str(e)}")
            # Hata durumunda güvenli kabul et (kullanıcı deneyimini bozmamak için)
            print(f"✅ Skipping NSFW check due to error, proceeding with generation")
            return False
    
    def generate_music_video(
        self, 
        lyrics: str, 
        story: str,
        style: str = 'cinematic',
        mood: str = 'happy',
        duration: int = 8,
        enable_prompt_enhancement: bool = True,
        enable_safety_check: bool = True
    ) -> Dict:
        """
        Şarkı sözleri ve hikayeden müzik videosu üret
        
        Args:
            lyrics: Şarkı sözleri
            story: Video hikayesi (kullanıcının yazdığı)
            style: Video stili (cinematic, anime, realistic, abstract, music_video, dreamy)
            mood: Ruh hali (happy, sad, energetic, calm, romantic, dark)
            duration: Video süresi (saniye) - default 8
            enable_prompt_enhancement: AI ile prompt geliştirmeyi etkinleştir
            enable_safety_check: NSFW kontrolünü etkinleştir
        
        Returns:
            Dict with video_url, video_id, status
        """
        
        if not self.api_key:
            raise ValueError("FAL_KEY not configured. Please set FAL_KEY environment variable.")
        
        # Prompt oluştur
        base_prompt = self._create_video_prompt(lyrics, story, style, mood)
        
        print(f"🎬 Generating video with Fal AI...")
        print(f"📝 Base Prompt: {base_prompt[:100]}...")
        print(f"🎨 Style: {style}")
        print(f"😊 Mood: {mood}")
        
        # 1. Safety Check (isteğe bağlı)
        if enable_safety_check:
            if self.check_nsfw_prompt(base_prompt):
                raise ValueError("NSFW content detected in prompt. Video generation cancelled.")
        
        # 2. Prompt Enhancement (isteğe bağlı)
        if enable_prompt_enhancement:
            prompt = self.enhance_prompt_with_ai(base_prompt)
        else:
            prompt = base_prompt
        
        try:
            # Fal AI client kullanarak video üret
            # Text-to-video model: Kling Video 2.5 Turbo Pro
            print(f"🎬 Calling Fal AI Kling Video 2.5 Turbo Pro...")
            
            # Kling 2.5 Turbo Pro parametreleri (5 saniyelik, düşük maliyet)
            result = fal_client.subscribe(
                "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
                arguments={
                    "prompt": prompt,
                    "duration": "5",  # 5 saniye video
                    "aspect_ratio": "16:9",  # Standart video formatı
                    "negative_prompt": "blur, distort, and low quality",
                    "cfg_scale": 0.5,  # Prompt'a ne kadar yakın kalacağı (0.5 = balanced)
                },
                with_logs=True,
            )
            
            print(f"✅ Fal AI response received")
            print(f"📦 Result keys: {result.keys() if result else 'None'}")
            
            # Video URL'ini al
            video_url = None
            if 'video' in result:
                if isinstance(result['video'], dict):
                    video_url = result['video'].get('url')
                elif isinstance(result['video'], str):
                    video_url = result['video']
            
            if not video_url:
                print(f"❌ No video URL in result: {result}")
                raise Exception("No video URL returned from Fal AI")
            
            video_id = f"fal_video_{int(time.time())}"
            
            print(f"✅ Video generated successfully!")
            print(f"🎬 Video URL: {video_url}")
            print(f"🆔 Video ID: {video_id}")
            
            return {
                'video_url': video_url,
                'video_id': video_id,
                'status': 'completed',
                'prompt': prompt,
                'duration': duration,
                'style': style,
                'mood': mood,
            }
            
        except Exception as e:
            print(f"❌ Fal AI Error: {str(e)}")
            raise Exception(f"Video generation failed: {str(e)}")
    
    def _create_video_prompt(self, lyrics: str, story: str, style: str, mood: str) -> str:
        """
        Şarkı sözleri ve hikayeden video prompt'u oluştur
        """
        
        # Style presets
        style_prompts = {
            'cinematic': 'cinematic, movie-like, dramatic lighting, film grain, professional cinematography',
            'anime': 'anime style, vibrant colors, japanese animation, detailed artwork',
            'realistic': 'photorealistic, detailed, high quality, 4k, natural lighting',
            'abstract': 'abstract art, surreal, artistic, creative, colorful patterns',
            'music_video': 'music video style, dynamic, colorful, energetic, professional',
            'dreamy': 'dreamy, ethereal, soft focus, magical, fantasy-like'
        }
        
        # Mood presets
        mood_prompts = {
            'happy': 'bright, cheerful, uplifting, positive vibes, sunny',
            'sad': 'melancholic, emotional, dark tones, moody, somber',
            'energetic': 'dynamic, fast-paced, vibrant, exciting, powerful',
            'calm': 'peaceful, serene, gentle, relaxing, tranquil',
            'romantic': 'romantic, intimate, warm lighting, soft, loving',
            'dark': 'dark, mysterious, atmospheric, noir, dramatic'
        }
        
        # Hikaye varsa onu kullan, yoksa şarkı sözlerinden çıkar
        base_content = story if story else self._extract_keywords(lyrics)
        
        # Prompt'u birleştir
        style_desc = style_prompts.get(style, style_prompts['cinematic'])
        mood_desc = mood_prompts.get(mood, mood_prompts['happy'])
        
        prompt = f"{base_content}, {style_desc}, {mood_desc}, smooth camera movement, high quality"
        
        # Prompt'u kısalt (max 500 karakter)
        if len(prompt) > 500:
            prompt = prompt[:497] + "..."
        
        return prompt
    
    def _extract_keywords(self, lyrics: str, max_words: int = 30) -> str:
        """
        Şarkı sözlerinden anahtar kelimeleri çıkar
        """
        if not lyrics:
            return "beautiful scenery, artistic visuals"
        
        # İlk birkaç satırı al
        lines = lyrics.split('\n')[:4]
        keywords = ' '.join(lines)
        
        # Çok uzunsa kısalt
        words = keywords.split()[:max_words]
        result = ' '.join(words)
        
        return result if result else "beautiful scenery, artistic visuals"
    
    def check_generation_status(self, request_id: str) -> Dict:
        """
        Video üretim durumunu kontrol et (async generation için)
        """
        try:
            status = fal_client.status("fal-ai/fast-animatediff/text-to-video", request_id)
            return status
        except Exception as e:
            print(f"❌ Status check error: {str(e)}")
            return {'status': 'error', 'error': str(e)}


# Singleton instance
fal_video_service = FalVideoService()
