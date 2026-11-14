import openai
import asyncio
import time
from typing import Dict, Any
from config.settings import settings
from models.schemas import MusicTheme, LyricsResponse

# Lyric styles: how a song in each style is built and how it flows
STYLE_GUIDES = {
    "pop": {"name": "Pop",
        "rules": "Catchy, everyday words, clear images. The hook is easy to sing along to.",
        "rhyme": "Rhyme line endings in AABB or ABAB.",
        "structure": "[Verse 1] 4 lines\n[Chorus] 4 lines\n[Verse 2] 4 lines\n[Chorus] 4 lines (same as before)"},
    "rap": {"name": "Rap / Hip-Hop",
        "rules": "Dense, rhythmic flow with confident delivery. Punchlines at the end of every 4 bars. Wordplay is welcome.",
        "rhyme": "Use multisyllable and internal rhymes inside lines, not only at line endings; keep the rhyme sound running across 2-4 bars.",
        "structure": "[Verse 1] 8 bars (8 lines)\n[Hook] 4 lines\n[Verse 2] 8 bars\n[Hook] 4 lines (same as before)"},
    "arabesk": {"name": "Arabesk",
        "rules": "Dramatic, heartfelt lament about fate, longing and pain. Long open vowels at line endings for melismatic singing; exclamations natural to the genre are welcome.",
        "rhyme": "Rhyme line endings in AAAB or AABB with strong, emotional end rhymes.",
        "structure": "[Verse 1] 4 lines\n[Nakarat] 4 lines\n[Verse 2] 4 lines\n[Nakarat] 4 lines (same as before)"},
    "rock": {"name": "Rock",
        "rules": "Raw, energetic, defiant. Short punchy lines and an anthem-like chorus to shout along.",
        "rhyme": "Rhyme line endings in AABB; strong one-syllable rhymes hit hardest.",
        "structure": "[Verse 1] 4 lines\n[Chorus] 4 lines\n[Verse 2] 4 lines\n[Chorus] 4 lines (same as before)"},
    "ballad": {"name": "Ballad",
        "rules": "Slow, intimate and tender. Longer flowing lines, every word sung with feeling.",
        "rhyme": "Rhyme line endings in ABAB with soft, open rhymes.",
        "structure": "[Verse 1] 4 lines\n[Chorus] 4 lines\n[Bridge] 2 lines\n[Chorus] 4 lines (same as before)"},
    "lofi": {"name": "Lo-fi",
        "rules": "Dreamy, laid-back and conversational, like a late-night thought. Few words, lots of space.",
        "rhyme": "Loose, soft slant rhymes are fine.",
        "structure": "[Verse] 4 short lines\n[Chorus] 2-3 lines\n[Verse 2] 4 short lines\n[Chorus] 2-3 lines (same as before)"},
    "folk": {"name": "Folk / Türkü",
        "rules": "Storytelling, simple honest words, images from nature and daily life. The refrain carries the story's heart.",
        "rhyme": "Rhyme line endings in AAAB (mani/türkü style) or AABB.",
        "structure": "[Kıta 1] 4 lines\n[Nakarat] 2-4 lines\n[Kıta 2] 4 lines\n[Nakarat] (same as before)"},
    "rnb": {"name": "R&B",
        "rules": "Smooth, warm and sensual. Lines end on open vowels for runs; repetition of short phrases is welcome.",
        "rhyme": "Rhyme line endings in AABB with smooth slant rhymes.",
        "structure": "[Verse 1] 4 lines\n[Chorus] 4 lines\n[Verse 2] 4 lines\n[Chorus] 4 lines (same as before)"},
}


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

    async def generate_lyrics(self, story: str, theme: MusicTheme, language: str = "tr", title: str = None, style: str = None) -> LyricsResponse:
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
            
            style_key = (style or "pop").lower()
            style_rules = STYLE_GUIDES.get(style_key, STYLE_GUIDES["pop"])
            theme_instruction = f"\nTheme guidance: {theme_guidance}" if theme_guidance else ""
            title_rule = f'- The chorus must contain the title "{title}" (it is the hook).' if title else ""

            full_prompt = f"""Write song lyrics in {output_lang} that tell THIS person's story. It is their song.

{title_line}--- THE USER'S STORY (their own words) ---
{story}
--- END ---
{theme_instruction}

STYLE: {style_rules["name"]}
{style_rules["rules"]}

Faithfulness (most important):
- The song is about exactly what the user wrote. Do not invent a different story, other characters, places or events.
- Every name, place, object and event in the story appears in the lyrics.
- Reuse the user's own most striking words and phrases (at least two), verbatim or almost verbatim, reshaped only to fit rhythm and rhyme. Put one of them in the chorus.
- Imagery and metaphors may only deepen what the user wrote, never replace it.
{title_rule}

Musicality:
- Lines in the same section have similar syllable counts (within 2), so they sing on the same melody.
- {style_rules["rhyme"]}
- The chorus is short, singable and repeats word for word.
- All lyrics in {output_lang} only.

Structure (the song is about 30-60 seconds, keep it compact):
{style_rules["structure"]}

Output ONLY the lyrics with the section headers in square brackets. Nothing else."""

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
                max_tokens=1200,
                temperature=0.8,
                # low penalties: a chorus has to repeat, and the user's words have to stay
                presence_penalty=0.2,
                frequency_penalty=0.1
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

    async def rhyme_lyrics(self, lyrics: str, story: str = None, style: str = None, language: str = "tr") -> str:
        """Kafiye Sihirbazı: same song, same meaning and words, stronger rhymes and flow."""
        langs = {"tr": "Türkçe", "en": "English", "es": "Spanish", "ar": "Arabic", "de": "German",
                 "fr": "French", "ko": "Korean", "zh": "Chinese", "it": "Italian"}
        output_lang = langs.get(language, "English")
        guide = STYLE_GUIDES.get((style or "pop").lower(), STYLE_GUIDES["pop"])
        story_block = f"\nThe user's story (keep its names, places and key phrases):\n{story}\n" if story else ""
        prompt = f"""Polish these {guide["name"]} song lyrics in {output_lang}. Keep the same song: same story, same section headers, same number of lines per section, and keep the user's names, places and key phrases.

Improve only the musicality:
- {guide["rhyme"]}
- Even out syllable counts inside each section (within 2) so lines sing on one melody.
- {guide["rules"]}
- The chorus stays identical every time it repeats.
{story_block}
--- LYRICS ---
{lyrics}
--- END ---

Output ONLY the improved lyrics with the section headers in square brackets."""
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a meticulous songwriter and lyric editor who perfects rhyme and flow without changing what a song is about."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()

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
