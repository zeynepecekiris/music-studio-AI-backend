import openai
import asyncio
import time
from typing import Dict, Any
from config.settings import settings
from models.schemas import MusicTheme, LyricsResponse

class OpenAIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Theme-specific prompts in Turkish
        self.theme_prompts = {
            MusicTheme.LOVE: {
                "tr": "Aşk temalı, romantik ve duygusal bir şarkı sözü yazın. Sevgiliyle olan güzel anıları, özlemi ve derin bağı anlatan sözler olsun.",
                "en": "Write romantic and emotional song lyrics about love. Include beautiful memories with a loved one, longing, and deep connection.",
                "es": "Escribe letras románticas y emocionales sobre el amor. Incluye hermosos recuerdos con un ser querido, anhelo y conexión profunda."
            },
            MusicTheme.FRIENDSHIP: {
                "tr": "Dostluk temalı, arkadaşlık bağının gücünü anlatan şarkı sözü yazın. Beraber geçirilen güzel zamanları ve dostluğun değerini vurgulayın.",
                "en": "Write song lyrics about friendship, highlighting the power of friendship bonds. Emphasize good times spent together and the value of friendship.",
                "es": "Escribe letras sobre la amistad, destacando el poder de los lazos de amistad. Enfatiza los buenos momentos compartidos y el valor de la amistad."
            },
            MusicTheme.COUNTRY: {
                "tr": "Memleket sevgisi temalı şarkı sözü yazın. Vatana olan bağlılığı, memleketinin güzelliklerini ve özlemini anlatan sözler olsun.",
                "en": "Write song lyrics about homeland love. Include loyalty to country, the beauty of homeland, and nostalgia.",
                "es": "Escribe letras sobre el amor a la patria. Incluye lealtad al país, la belleza de la tierra natal y la nostalgia."
            },
            MusicTheme.NOSTALGIA: {
                "tr": "Nostalji temalı şarkı sözü yazın. Geçmişin güzel anılarını, kayıp zamanları ve o dönemlere olan özlemi anlatan sözler.",
                "en": "Write nostalgic song lyrics about beautiful memories from the past, lost times, and longing for those periods.",
                "es": "Escribe letras nostálgicas sobre hermosos recuerdos del pasado, tiempos perdidos y añoranza por esos períodos."
            },
            MusicTheme.HOPE: {
                "tr": "Umut temalı şarkı sözü yazın. Gelecekteki güzel günlere olan inancı, zorluklara rağmen umudunu kaybetmemeyi anlatan sözler.",
                "en": "Write hopeful song lyrics about faith in beautiful future days, not losing hope despite difficulties.",
                "es": "Escribe letras esperanzadoras sobre la fe en días futuros hermosos, no perder la esperanza a pesar de las dificultades."
            },
            MusicTheme.FAMILY: {
                "tr": "Aile temalı şarkı sözü yazın. Ailenin sıcaklığını, birlik beraberliği ve aile bağlarının gücünü anlatan sözler.",
                "en": "Write family-themed song lyrics about family warmth, unity, and the strength of family bonds.",
                "es": "Escribe letras familiares sobre la calidez familiar, la unidad y la fuerza de los lazos familiares."
            },
            MusicTheme.ADVENTURE: {
                "tr": "Macera temalı şarkı sözü yazın. Yeni yerler keşfetme, heyecan verici yolculuklar ve özgürlük hissini anlatan sözler.",
                "en": "Write adventure-themed song lyrics about discovering new places, exciting journeys, and the feeling of freedom.",
                "es": "Escribe letras de aventura sobre descubrir nuevos lugares, viajes emocionantes y la sensación de libertad."
            },
            MusicTheme.PEACE: {
                "tr": "Barış temalı şarkı sözü yazın. İç huzuru, sakinlik ve dünyada barış özlemini anlatan sözler.",
                "en": "Write peace-themed song lyrics about inner peace, tranquility, and longing for world peace.",
                "es": "Escribe letras de paz sobre la paz interior, la tranquilidad y el anhelo de paz mundial."
            },
            MusicTheme.HEARTBREAK: {
                "tr": "Kırık kalp temalı şarkı sözü yazın. Ayrılık acısını, kayıp sevgiyi ve kalp kırıklığını anlatan sözler.",
                "en": "Write heartbreak-themed song lyrics about the pain of separation, lost love, and heartbreak.",
                "es": "Escribe letras de desamor sobre el dolor de la separación, el amor perdido y la desilusión."
            },
            MusicTheme.HAPPINESS: {
                "tr": "Mutluluk temalı şarkı sözü yazın. Yaşamın güzel anlarını, sevinci ve pozitif enerjiyi anlatan sözler.",
                "en": "Write happiness-themed song lyrics about life's beautiful moments, joy, and positive energy.",
                "es": "Escribe letras de felicidad sobre los hermosos momentos de la vida, la alegría y la energía positiva."
            },
            MusicTheme.SADNESS: {
                "tr": "Hüzün temalı şarkı sözü yazın. Üzüntüyü, acıyı ve duygusal derinliği anlatan sözler.",
                "en": "Write sadness-themed song lyrics about sorrow, pain, and emotional depth.",
                "es": "Escribe letras de tristeza sobre la pena, el dolor y la profundidad emocional."
            },
            MusicTheme.CELEBRATION: {
                "tr": "Kutlama temalı şarkı sözü yazın. Başarıları, özel günleri ve mutlu anları kutlayan sözler.",
                "en": "Write celebration-themed song lyrics celebrating achievements, special days, and happy moments.",
                "es": "Escribe letras de celebración celebrando logros, días especiales y momentos felices."
            },
            MusicTheme.MOTIVATION: {
                "tr": "Motivasyon temalı şarkı sözü yazın. İlham verici, güçlendirici ve hedeflere ulaşma konusunda motive edici sözler.",
                "en": "Write motivation-themed song lyrics that are inspiring, empowering, and motivating to achieve goals.",
                "es": "Escribe letras motivacionales que sean inspiradoras, empoderadoras y motivadoras para alcanzar metas."
            }
        }

    async def generate_lyrics(self, story: str, theme: MusicTheme, language: str = "tr", title: str = None) -> LyricsResponse:
        """Generate song lyrics based on story, title and theme using OpenAI"""
        start_time = time.time()

        # Output language mapping
        output_lang_map = {
            "tr": "Türkçe", "en": "English", "es": "Spanish", "ar": "Arabic",
            "de": "German", "fr": "French", "ko": "Korean", "zh": "Chinese", "it": "Italian"
        }

        # Language-specific system messages
        system_prompts = {
            "tr": "Sen profesyonel bir şarkı sözü yazarısın. Verilen hikayeden ilham alarak özgün, duygusal ve şiirsel Türkçe şarkı sözleri yazarsın.",
            "en": "You are a professional songwriter who writes original, emotional, and poetic song lyrics in English based on the given story.",
            "es": "Eres un compositor profesional que escribe letras de canciones originales, emotivas y poéticas en español basadas en la historia dada.",
            "de": "Du bist ein professioneller Songwriter, der originelle, emotionale und poetische deutsche Songtexte basierend auf der gegebenen Geschichte schreibt.",
            "fr": "Tu es un parolier professionnel qui écrit des paroles de chansons originales, émotionnelles et poétiques en français basées sur l'histoire donnée.",
            "ko": "당신은 주어진 이야기를 바탕으로 독창적이고 감성적이며 시적인 한국어 노래 가사를 쓰는 전문 작사가입니다.",
            "zh": "你是一位专业的词曲作家，根据给定的故事创作原创、情感丰富且富有诗意的中文歌词。",
            "it": "Sei un paroliere professionista che scrive testi di canzoni originali, emotivi e poetici in italiano basati sulla storia data.",
            "ar": "أنت كاتب أغاني محترف يكتب كلمات أغاني أصلية وعاطفية وشعرية باللغة العربية بناءً على القصة المعطاة.",
        }

        try:
            output_lang = output_lang_map.get(language, "English")
            system_msg = system_prompts.get(language, system_prompts["en"])

            # Build title line for prompt
            title_line = f'Title: "{title}"\n' if title else ""
            
            # Get theme-specific guidance
            theme_guidance = self.theme_prompts.get(theme, {}).get(language, "")
            
            # Create example to show the format
            example_format = """
Example format:
[Verse 1]
Golden beaches calling my name
Sunset colors paint the sky
Temple bells echo through the rain
Where the palm trees touch the sky

[Chorus]
Take me there, to that distant shore
Where my heart can finally soar
In the land of smiles and dreams
Nothing's ever as it seems

[Verse 2]
Street food vendors light the night
Tuk-tuks racing through the crowd
Ancient wisdom shining bright
In this place I'm finally found

[Bridge]
Every moment feels brand new
Every color, every view

[Final Chorus]
Take me there, to that distant shore
Where my heart can finally soar
In the land of smiles and dreams
Living out my wildest dreams
"""
            
            theme_instruction = f"\nTheme guidance: {theme_guidance}" if theme_guidance else ""

            full_prompt = f"""You are a world-class songwriter. Your task is to write ORIGINAL, POETIC, ARTISTIC song lyrics in {output_lang}.

{title_line}The following story is ONLY for inspiration — do NOT copy, translate, or paraphrase it:
--- STORY (for inspiration only) ---
{story}
--- END STORY ---
{theme_instruction}

{example_format}

Write a COMPLETE ORIGINAL SONG in {output_lang} that captures the EMOTION and FEELING of the story, not the literal words.

Rules:
- Every single line must be a NEW, ORIGINAL poetic expression — never copied from the story
- Use metaphors, imagery, symbolism, and poetic language
- Structure: [Verse 1] (4-6 lines), [Chorus] (3-4 lines), [Verse 2] (4-6 lines), [Bridge] (2-4 lines), [Final Chorus] (3-4 lines)
- All lyrics must be in {output_lang} only
- Rhyme naturally and musically
- Make the chorus memorable and singable
- Each verse should deepen the emotional journey

Output ONLY the song lyrics with section headers. Nothing else."""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_msg
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.92,
                presence_penalty=0.9,
                frequency_penalty=0.85
            )

            # Extract lyrics from response
            lyrics = response.choices[0].message.content.strip()
            processing_time = time.time() - start_time

            # Count words
            word_count = len(lyrics.split())

            return LyricsResponse(
                lyrics=lyrics,
                theme=theme,
                language=language,
                processing_time=processing_time,
                word_count=word_count
            )

        except openai.RateLimitError:
            raise Exception("OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error generating lyrics: {str(e)}")

    async def improve_lyrics(self, original_lyrics: str, story: str, theme: MusicTheme) -> str:
        """Improve existing lyrics based on feedback"""
        try:
            prompt = f"""
Aşağıdaki şarkı sözlerini daha iyi hale getirin:

Orijinal Hikaye: "{story}"
Tema: {theme.value}
Mevcut Şarkı Sözü:
{original_lyrics}

Lütfen şarkı sözünü geliştirin:
- Daha akıcı hale getirin
- Kafiye düzenini iyileştirin  
- Duygusal etkiyi artırın
- Hikayeyle bağlantıyı güçlendirin
- Aynı formatı koruyun (Verse, Chorus, vs.)
"""

            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Sen şarkı sözlerini geliştiren uzman bir editörsün."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Error improving lyrics: {str(e)}")

    async def generate_title(self, lyrics: str, theme: MusicTheme) -> str:
        """Generate a catchy title for the song"""
        try:
            prompt = f"""
Bu şarkı sözlerine uygun, çekici bir başlık öner:

Tema: {theme.value}
Şarkı Sözü:
{lyrics[:500]}...

Başlık:
- Kısa ve akılda kalıcı olsun (3-6 kelime)
- Şarkının ruhunu yansıtsın
- Türkçe olsun
- Sadece başlığı döndür, açıklama yapma
"""

            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Cheaper for simple tasks
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.9
            )
            
            return response.choices[0].message.content.strip().replace('"', '')
            
        except Exception as e:
            return f"{theme.value.title()} Şarkısı"  # Fallback title

# Singleton instance
openai_service = OpenAIService()
