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

    async def generate_lyrics(self, story: str, theme: MusicTheme, language: str = "tr") -> LyricsResponse:
        """Generate song lyrics based on story and theme using OpenAI"""
        start_time = time.time()
        
        # Language-specific configurations
        language_configs = {
            "tr": {
                "story_label": "Kullanıcının Hikayesi",
                "instruction": "Lütfen bu hikayeye uygun, {theme} temalı bir şarkı sözü yazın.",
                "requirements": """Şarkı sözü:
- 4 kıta (verse) olsun
- Her kıta 4 satır olsun  
- Nakarat (chorus) ekleyin
- Duygusal ve akılda kalıcı olsun
- Hikayedeki detayları kullanın
- Türkçe olarak yazın
- Şarkı formatında olsun (Verse 1, Chorus, Verse 2, vs.)""",
                "system_message": "Sen profesyonel bir şarkı sözü yazarısın. Kullanıcıların hikayelerini duygusal ve kaliteli şarkı sözlerine dönüştürüyorsun."
            },
            "en": {
                "story_label": "User's Story",
                "instruction": "Please write song lyrics with {theme} theme based on this story.",
                "requirements": """Song lyrics should:
- Have 4 verses
- Each verse should have 4 lines
- Include a chorus
- Be emotional and memorable
- Use details from the story
- Be written in English
- Follow song format (Verse 1, Chorus, Verse 2, etc.)""",
                "system_message": "You are a professional songwriter. You transform users' stories into emotional and high-quality song lyrics."
            },
            "es": {
                "story_label": "Historia del Usuario",
                "instruction": "Por favor escribe letras de canción con tema {theme} basadas en esta historia.",
                "requirements": """Las letras deben:
- Tener 4 versos
- Cada verso debe tener 4 líneas
- Incluir un estribillo
- Ser emocionales y memorables
- Usar detalles de la historia
- Estar escritas en español
- Seguir formato de canción (Verso 1, Estribillo, Verso 2, etc.)""",
                "system_message": "Eres un compositor profesional. Transformas las historias de los usuarios en letras emotivas y de alta calidad."
            },
            "ar": {
                "story_label": "قصة المستخدم",
                "instruction": "يرجى كتابة كلمات أغنية بموضوع {theme} بناءً على هذه القصة.",
                "requirements": """يجب أن تكون كلمات الأغنية:
- 4 مقاطع
- كل مقطع يحتوي على 4 أسطر
- تتضمن لازمة
- عاطفية ولا تُنسى
- تستخدم تفاصيل من القصة
- مكتوبة بالعربية
- تتبع تنسيق الأغنية (المقطع 1، اللازمة، المقطع 2، إلخ)""",
                "system_message": "أنت كاتب أغاني محترف. تحول قصص المستخدمين إلى كلمات أغاني عاطفية وعالية الجودة."
            },
            "de": {
                "story_label": "Geschichte des Benutzers",
                "instruction": "Bitte schreibe Songtexte mit dem Thema {theme} basierend auf dieser Geschichte.",
                "requirements": """Songtexte sollten:
- 4 Strophen haben
- Jede Strophe sollte 4 Zeilen haben
- Einen Refrain enthalten
- Emotional und einprägsam sein
- Details aus der Geschichte verwenden
- Auf Deutsch geschrieben sein
- Songformat folgen (Strophe 1, Refrain, Strophe 2, etc.)""",
                "system_message": "Du bist ein professioneller Songwriter. Du verwandelst die Geschichten der Benutzer in emotionale und hochwertige Songtexte."
            },
            "fr": {
                "story_label": "Histoire de l'utilisateur",
                "instruction": "Veuillez écrire des paroles de chanson avec le thème {theme} basées sur cette histoire.",
                "requirements": """Les paroles doivent:
- Avoir 4 couplets
- Chaque couplet doit avoir 4 lignes
- Inclure un refrain
- Être émotionnelles et mémorables
- Utiliser des détails de l'histoire
- Être écrites en français
- Suivre le format de chanson (Couplet 1, Refrain, Couplet 2, etc.)""",
                "system_message": "Vous êtes un auteur-compositeur professionnel. Vous transformez les histoires des utilisateurs en paroles émotionnelles et de haute qualité."
            },
            "it": {
                "story_label": "Storia dell'utente",
                "instruction": "Per favore scrivi testi di canzoni con tema {theme} basati su questa storia.",
                "requirements": """I testi dovrebbero:
- Avere 4 strofe
- Ogni strofa dovrebbe avere 4 righe
- Includere un ritornello
- Essere emotivi e memorabili
- Usare dettagli dalla storia
- Essere scritti in italiano
- Seguire il formato della canzone (Strofa 1, Ritornello, Strofa 2, ecc.)""",
                "system_message": "Sei un autore di canzoni professionista. Trasformi le storie degli utenti in testi emotivi e di alta qualità."
            },
            "ko": {
                "story_label": "사용자의 이야기",
                "instruction": "이 이야기를 바탕으로 {theme} 테마의 노래 가사를 작성해주세요.",
                "requirements": """가사는:
- 4개의 절이 있어야 함
- 각 절은 4줄이어야 함
- 후렴구를 포함
- 감성적이고 기억에 남아야 함
- 이야기의 세부 사항을 사용
- 한국어로 작성
- 노래 형식을 따라야 함 (1절, 후렴, 2절 등)""",
                "system_message": "당신은 전문 작사가입니다. 사용자의 이야기를 감성적이고 고품질의 노래 가사로 변환합니다."
            },
            "zh": {
                "story_label": "用户的故事",
                "instruction": "请根据这个故事写一首{theme}主题的歌词。",
                "requirements": """歌词应该:
- 有4个段落
- 每个段落应该有4行
- 包括副歌
- 情感丰富且令人难忘
- 使用故事中的细节
- 用中文写
- 遵循歌曲格式（第1节、副歌、第2节等）""",
                "system_message": "你是一位专业的词曲作者。你将用户的故事转化为情感丰富且高质量的歌词。"
            }
        }
        
        try:
            # Get theme-specific prompt
            theme_prompt = self.theme_prompts.get(theme, {}).get(language, self.theme_prompts[MusicTheme.LOVE]["en"])
            
            # Get language config (default to English if not found)
            lang_config = language_configs.get(language, language_configs["en"])
            
            # Create the full prompt in user's language
            full_prompt = f"""
{theme_prompt}

{lang_config['story_label']}: "{story}"

{lang_config['instruction'].format(theme=theme.value)}

{lang_config['requirements']}

Format:
[Verse 1]
...

[Chorus] 
...

[Verse 2]
...

[Chorus]
...
"""

            # Call OpenAI API with language-specific system message
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": lang_config['system_message']
                    },
                    {
                        "role": "user", 
                        "content": full_prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.8,
                presence_penalty=0.1,
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
