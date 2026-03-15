"""
🎬 Video Service
music_video.mp4 loop + audio merge ile klip oluşturma servisi
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Template video: 5 saniyelik sabit video (assets/music_video.mp4)
TEMPLATE_VIDEO_DURATION = 5  # saniye


class VideoService:
    """Klip oluşturma servisi - music_video.mp4 loop + audio merge"""
    
    def __init__(self, template_video_path: str = None):
        """
        Args:
            template_video_path: Template video dosyasının path'i
        """
        # music_video.mp4 -> project root / assets / music_video.mp4
        self.template_video_path = template_video_path or os.path.join(
            os.path.dirname(__file__),
            '..',
            'assets',
            'music_video.mp4'
        )
        
        # FFmpeg kurulu mu kontrol et
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """FFmpeg kurulu mu kontrol et"""
        try:
            subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                check=True
            )
            logger.info("✅ FFmpeg is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ FFmpeg is not installed!")
            raise RuntimeError(
                "FFmpeg is not installed. Please install it: "
                "brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            )
    
    def create_music_clip(
        self,
        audio_path: str,
        song_title: str,
        duration: int,
        output_path: Optional[str] = None
    ) -> str:
        """
        Müzik klibi oluştur: music_video.mp4 loop + audio merge
        
        5 saniyelik template video şarkı süresi boyunca loop edilir,
        müzik ile birleştirilir ve tek bir MP4 dosyası olarak export edilir.
        
        Args:
            audio_path: Müzik dosyasının LOCAL disk path'i
            song_title: Şarkı başlığı
            duration: Şarkı süresi (saniye)
            output_path: Çıktı video path'i (opsiyonel)
            
        Returns:
            str: Oluşturulan video dosyasının path'i
        """
        logger.info(f"🎬 Creating music clip for: {song_title}")
        logger.info(f"📊 Music duration: {duration}s, Video loop: {TEMPLATE_VIDEO_DURATION}s")
        logger.info(f"🎵 Audio path: {audio_path}")
        
        # Audio dosyası mevcut mu?
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Geçici dosyalar için klasör
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. Template video'yu kontrol et
            if not os.path.exists(self.template_video_path):
                raise FileNotFoundError(
                    f"Template video not found: {self.template_video_path}"
                )
            
            # 2. Output path belirle
            if output_path is None:
                safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in song_title)
                output_path = os.path.join(
                    temp_dir,
                    f"clip_{safe_title}.mp4"
                )
            
            # 3. Video + Audio birleştir (loop)
            self._merge_video_audio(
                template_video_path=self.template_video_path,
                audio_path=audio_path,
                output_path=output_path,
                duration=duration,
                song_title=song_title,
                artist_name=""
            )
            
            logger.info(f"✅ Music clip created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error creating music clip: {e}")
            raise
    
    def _merge_video_audio(
        self,
        template_video_path: str,
        audio_path: str,
        output_path: str,
        duration: int,
        song_title: str,
        artist_name: str
    ):
        """
        Template video ile müziği birleştir
        
        FFmpeg ile:
        1. Template video'yu loop'la (şarkı süresince)
        2. Müziği ekle
        3. Instagram Story formatında (1080x1920) export et
        """
        logger.info("🎬 Merging video and audio with FFmpeg...")
        
        # Template video süresini al
        template_duration = self._get_video_duration(template_video_path)
        logger.info(f"📊 Template video duration: {template_duration}s")
        
        # Kaç kez loop etmeli?
        loop_count = max(1, int(duration / template_duration) + 1)
        logger.info(f"🔄 Loop count: {loop_count}")
        
        # FFmpeg komutu
        # -stream_loop: Video'yu loop'la
        # -i: Input dosyalar
        # -map: Stream mapping (video template'ten, audio müzikten)
        # -c:v: Video codec (H.264)
        # -preset: Encoding hızı (ultrafast, fast, medium, slow)
        # -c:a: Audio codec (AAC)
        # -b:a: Audio bitrate
        # -shortest: En kısa stream'e göre kes
        # -y: Overwrite
        
        cmd = [
            'ffmpeg',
            '-stream_loop', str(loop_count),
            '-i', template_video_path,
            '-i', audio_path,
            '-map', '0:v',  # Video template'ten
            '-map', '1:a',  # Audio müzik dosyasından
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-profile:v', 'high',
            '-level', '4.2',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-shortest',  # Müzik bitince kes
            '-movflags', '+faststart',  # Web streaming için optimize et
            '-y',  # Overwrite
            output_path
        ]
        
        logger.info(f"🎬 Running FFmpeg command...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 dakika timeout
            )
            
            logger.info("✅ FFmpeg completed successfully")
            logger.debug(f"FFmpeg output: {result.stdout}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg error: {e.stderr}")
            raise RuntimeError(f"FFmpeg failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg timeout")
            raise RuntimeError("Video creation timed out")
    
    def _get_video_duration(self, video_path: str) -> float:
        """Video süresini al (saniye)"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    
    def add_text_overlay(
        self,
        video_path: str,
        output_path: str,
        song_title: str,
        artist_name: str
    ):
        """
        Video'ya text overlay ekle (opsiyonel)
        Şarkı adı ve sanatçı adını video üzerine yaz
        """
        logger.info("✍️ Adding text overlay...")
        
        # FFmpeg drawtext filter
        # Font: Arial veya system default
        # Pozisyon: Alt kısım, ortalanmış
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', (
                f"drawtext=text='{song_title}':"
                f"fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-200:"
                f"shadowcolor=black:shadowx=2:shadowy=2,"
                f"drawtext=text='{artist_name}':"
                f"fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h-140:"
                f"shadowcolor=black:shadowx=2:shadowy=2"
            ),
            '-c:a', 'copy',
            '-y',
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info("✅ Text overlay added")
