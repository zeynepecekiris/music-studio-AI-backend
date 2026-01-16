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
                "instruction": "Bu hikayeyi 2 kıtalık şarkı sözüne dönüştür. Kullanıcının YAZDıĞı CÜMLELERİ DOĞRUDAN KULLAN.",
                "requirements": """KESİN YAPISAL KURALLAR:
1. TAM OLARAK 2 kıta (verse) yaz - 3 veya 4 kıta YASAK
2. 1 nakarat (chorus) yaz
3. Her kıta tam 4 satır olmalı

KESİN İÇERİK KURALLARI:
1. Kullanıcının hikayesindeki AYNI KELİMELERİ ve AYNI CÜMLELERİ kullan
2. Kullanıcının yazdığı ifadeleri değiştirme, sadece şarkı formatına koy
3. Kullanıcının cümlelerini al ve satırlara böl
4. Sadece cümleler arası geçişler için 1-2 kelime ekleyebilirsin
5. Nakaratı kullanıcının ana fikrinden oluştur

ÖRNEK DÖNÜŞÜM:
Hikaye: "Seninle geçirdiğim her an çok güzeldi. Gözlerinde kaybolurdum. Şimdi sen yoksun, ben yapayalnızım."

[Verse 1]
Seninle geçirdiğim her an çok güzeldi
Gözlerinde kaybolurdum
Şimdi sen yoksun
Ben yapayalnızım

Format: [Verse 1], [Chorus], [Verse 2], [Chorus] - BAŞKA FORMAT KULLANMA""",
                "system_message": "Sen bir şarkı formatçısısın. Kullanıcının yazdığı hikayeyi KELİMESİ KELİMESİNE alıp şarkı formatına sokuyorsun. YENİ CÜMLELER YAZMA, kullanıcının yazdıklarını kullan. Sadece 2 verse + 1 chorus yaz."
            },
            "en": {
                "story_label": "User's Story",
                "instruction": "Transform this story into 2-verse song lyrics. Use the user's EXACT WORDS directly.",
                "requirements": """STRICT STRUCTURAL RULES:
1. Write EXACTLY 2 verses - 3 or 4 verses are FORBIDDEN
2. Write 1 chorus
3. Each verse must have exactly 4 lines

STRICT CONTENT RULES:
1. Use the SAME WORDS and SAME SENTENCES from the user's story
2. Don't change user's phrases, just put them in song format
3. Take user's sentences and break them into lines
4. You may only add 1-2 words for transitions between sentences
5. Create chorus from user's main idea

EXAMPLE TRANSFORMATION:
Story: "Every moment with you was beautiful. I got lost in your eyes. Now you're gone and I'm all alone."

[Verse 1]
Every moment with you was beautiful
I got lost in your eyes
Now you're gone
And I'm all alone

Format: [Verse 1], [Chorus], [Verse 2], [Chorus] - DO NOT USE OTHER FORMATS""",
                "system_message": "You are a song formatter. You take the user's story WORD FOR WORD and put it into song format. DO NOT WRITE NEW SENTENCES, use what the user wrote. Only write 2 verses + 1 chorus."
            },
            "es": {
                "story_label": "Historia del Usuario",
                "instruction": "Transforma esta historia en letras de 2 versos. Usa las PALABRAS EXACTAS del usuario directamente.",
                "requirements": """REGLAS ESTRUCTURALES ESTRICTAS:
1. Escribe EXACTAMENTE 2 versos - 3 o 4 versos están PROHIBIDOS
2. Escribe 1 estribillo
3. Cada verso debe tener exactamente 4 líneas

REGLAS DE CONTENIDO ESTRICTAS:
1. Usa las MISMAS PALABRAS y MISMAS FRASES de la historia del usuario
2. No cambies las frases del usuario, solo ponlas en formato de canción
3. Toma las frases del usuario y divídelas en líneas
4. Solo puedes añadir 1-2 palabras para transiciones entre frases
5. Crea el estribillo de la idea principal del usuario

EJEMPLO DE TRANSFORMACIÓN:
Historia: "Cada momento contigo fue hermoso. Me perdía en tus ojos. Ahora no estás y estoy solo."

[Verso 1]
Cada momento contigo fue hermoso
Me perdía en tus ojos
Ahora no estás
Y estoy solo

Formato: [Verso 1], [Estribillo], [Verso 2], [Estribillo] - NO USES OTROS FORMATOS""",
                "system_message": "Eres un formateador de canciones. Tomas la historia del usuario PALABRA POR PALABRA y la pones en formato de canción. NO ESCRIBAS NUEVAS FRASES, usa lo que el usuario escribió. Solo escribe 2 versos + 1 estribillo."
            },
            "ar": {
                "story_label": "قصة المستخدم",
                "instruction": "حول هذه القصة إلى كلمات أغنية من مقطعين. استخدم الكلمات الدقيقة للمستخدم مباشرة.",
                "requirements": """قواعد هيكلية صارمة:
1. اكتب مقطعين بالضبط - 3 أو 4 مقاطع ممنوعة
2. اكتب لازمة واحدة
3. كل مقطع يجب أن يحتوي على 4 أسطر بالضبط

قواعد محتوى صارمة:
1. استخدم نفس الكلمات ونفس الجمل من قصة المستخدم
2. لا تغير عبارات المستخدم، فقط ضعها في تنسيق الأغنية
3. خذ جمل المستخدم واقسمها إلى أسطر
4. يمكنك فقط إضافة كلمة أو كلمتين للانتقالات بين الجمل
5. أنشئ اللازمة من الفكرة الرئيسية للمستخدم

التنسيق: [المقطع 1]، [اللازمة]، [المقطع 2]، [اللازمة] - لا تستخدم تنسيقات أخرى""",
                "system_message": "أنت منسق أغاني. تأخذ قصة المستخدم كلمة بكلمة وتضعها في تنسيق الأغنية. لا تكتب جملاً جديدة، استخدم ما كتبه المستخدم. اكتب فقط مقطعين + لازمة واحدة."
            },
            "de": {
                "story_label": "Geschichte des Benutzers",
                "instruction": "Verwandle diese Geschichte in 2-strophige Songtexte. Verwende die EXAKTEN WORTE des Benutzers direkt.",
                "requirements": """STRIKTE STRUKTURREGELN:
1. Schreibe GENAU 2 Strophen - 3 oder 4 Strophen sind VERBOTEN
2. Schreibe 1 Refrain
3. Jede Strophe muss genau 4 Zeilen haben

STRIKTE INHALTSREGELN:
1. Verwende die GLEICHEN WORTE und GLEICHEN SÄTZE aus der Geschichte des Benutzers
2. Ändere die Phrasen des Benutzers nicht, setze sie nur in Songformat
3. Nimm die Sätze des Benutzers und teile sie in Zeilen auf
4. Du darfst nur 1-2 Wörter für Übergänge zwischen Sätzen hinzufügen
5. Erstelle den Refrain aus der Hauptidee des Benutzers

Format: [Strophe 1], [Refrain], [Strophe 2], [Refrain] - VERWENDE KEINE ANDEREN FORMATE""",
                "system_message": "Du bist ein Song-Formatierer. Du nimmst die Geschichte des Benutzers WORT FÜR WORT und setzt sie in Songformat. SCHREIBE KEINE NEUEN SÄTZE, verwende was der Benutzer geschrieben hat. Schreibe nur 2 Strophen + 1 Refrain."
            },
            "fr": {
                "story_label": "Histoire de l'utilisateur",
                "instruction": "Transformez cette histoire en paroles de 2 couplets. Utilisez les MOTS EXACTS de l'utilisateur directement.",
                "requirements": """RÈGLES STRUCTURELLES STRICTES:
1. Écrivez EXACTEMENT 2 couplets - 3 ou 4 couplets sont INTERDITS
2. Écrivez 1 refrain
3. Chaque couplet doit avoir exactement 4 lignes

RÈGLES DE CONTENU STRICTES:
1. Utilisez les MÊMES MOTS et MÊMES PHRASES de l'histoire de l'utilisateur
2. Ne changez pas les phrases de l'utilisateur, mettez-les juste en format chanson
3. Prenez les phrases de l'utilisateur et divisez-les en lignes
4. Vous ne pouvez ajouter que 1-2 mots pour les transitions entre phrases
5. Créez le refrain à partir de l'idée principale de l'utilisateur

Format: [Couplet 1], [Refrain], [Couplet 2], [Refrain] - N'UTILISEZ PAS D'AUTRES FORMATS""",
                "system_message": "Vous êtes un formateur de chansons. Vous prenez l'histoire de l'utilisateur MOT POUR MOT et la mettez en format chanson. N'ÉCRIVEZ PAS DE NOUVELLES PHRASES, utilisez ce que l'utilisateur a écrit. Écrivez seulement 2 couplets + 1 refrain."
            },
            "it": {
                "story_label": "Storia dell'utente",
                "instruction": "Trasforma questa storia in testi di 2 strofe. Usa le PAROLE ESATTE dell'utente direttamente.",
                "requirements": """REGOLE STRUTTURALI RIGOROSE:
1. Scrivi ESATTAMENTE 2 strofe - 3 o 4 strofe sono VIETATE
2. Scrivi 1 ritornello
3. Ogni strofa deve avere esattamente 4 righe

REGOLE DI CONTENUTO RIGOROSE:
1. Usa le STESSE PAROLE e STESSE FRASI dalla storia dell'utente
2. Non cambiare le frasi dell'utente, mettile solo in formato canzone
3. Prendi le frasi dell'utente e dividile in righe
4. Puoi aggiungere solo 1-2 parole per transizioni tra frasi
5. Crea il ritornello dall'idea principale dell'utente

Formato: [Strofa 1], [Ritornello], [Strofa 2], [Ritornello] - NON USARE ALTRI FORMATI""",
                "system_message": "Sei un formattatore di canzoni. Prendi la storia dell'utente PAROLA PER PAROLA e la metti in formato canzone. NON SCRIVERE NUOVE FRASI, usa ciò che l'utente ha scritto. Scrivi solo 2 strofe + 1 ritornello."
            },
            "ko": {
                "story_label": "사용자의 이야기",
                "instruction": "이 이야기를 2절 가사로 변환하세요. 사용자의 정확한 단어를 직접 사용하세요.",
                "requirements": """엄격한 구조 규칙:
1. 정확히 2개의 절만 작성 - 3개 또는 4개 절은 금지
2. 1개의 후렴구 작성
3. 각 절은 정확히 4줄이어야 함

엄격한 내용 규칙:
1. 사용자 이야기의 같은 단어와 같은 문장을 사용하세요
2. 사용자의 구문을 변경하지 말고 노래 형식으로만 배치하세요
3. 사용자의 문장을 가져와서 줄로 나누세요
4. 문장 사이의 전환을 위해 1-2개 단어만 추가할 수 있습니다
5. 사용자의 주요 아이디어로 후렴구를 만드세요

형식: [1절], [후렴], [2절], [후렴] - 다른 형식 사용 금지""",
                "system_message": "당신은 노래 포맷터입니다. 사용자의 이야기를 단어 그대로 가져와서 노래 형식으로 만듭니다. 새로운 문장을 쓰지 말고 사용자가 쓴 것을 사용하세요. 2절 + 1 후렴구만 작성하세요."
            },
            "zh": {
                "story_label": "用户的故事",
                "instruction": "将这个故事转换为2节歌词。直接使用用户的确切词语。",
                "requirements": """严格的结构规则:
1. 准确写2节 - 禁止写3或4节
2. 写1个副歌
3. 每节必须恰好4行

严格的内容规则:
1. 使用用户故事中相同的词语和相同的句子
2. 不要改变用户的短语，只将它们放入歌曲格式
3. 取用户的句子并将其分成行
4. 只能添加1-2个词用于句子之间的过渡
5. 从用户的主要思想创建副歌

格式：[第1节]、[副歌]、[第2节]、[副歌] - 不要使用其他格式""",
                "system_message": "你是歌曲格式化器。你逐字逐句地采用用户的故事并将其转换为歌曲格式。不要写新句子，使用用户写的内容。只写2节 + 1副歌。"
            }
- 只在必要时添加连接短语和押韵词
- 70-80%的歌词应该是用户自己的话
- 以专业音乐家的风格编排，但保留用户的原始短语
- 副歌应该反映故事的主要思想
- 用中文写
- 格式：[第1节]、[副歌]、[第2节]、[副歌]""",
                "system_message": "你是一位专业的歌词编辑。你将用户自己写的故事转化为歌曲格式。你完全保持用户的句子原样，只进行最小的调整以适应韵律和节奏。"
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

Format örneği:
[Verse 1]
(kullanıcının hikayesinden cümleler - 4 satır)

[Chorus]
(ana fikir - 4 satır)

[Verse 2]
(kullanıcının hikayesinden cümleler - 4 satır)

[Chorus]
(aynı nakarat tekrar)
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
