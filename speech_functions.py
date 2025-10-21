import io
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment

def transcribe_audio(audio_bytes):
    """
    Transcribes spoken words from audio bytes into text using Google's Speech Recognition.

    Args:
        audio_bytes (bytes): The audio data recorded from the user.

    Returns:
        str: The transcribed text, or None if transcription fails.
    """
    if not audio_bytes:
        return None

    try:
        # Convert raw bytes to an AudioSegment object
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Export as WAV to a memory buffer
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        # Use the WAV buffer with SpeechRecognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_buffer) as source:
            audio_data = recognizer.record(source)
        
        # Recognize speech using Google's free web API
        text = recognizer.recognize_google(audio_data)
        return text.lower()
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"An error occurred during audio transcription: {e}")
        return None

def text_to_speech(text):
    """
    Converts a string of text into speech audio bytes using Google Text-to-Speech.

    Args:
        text (str): The text to be converted to speech.

    Returns:
        bytes: The generated speech as audio bytes, or None if it fails.
    """
    if not text:
        return None
        
    try:
        tts = gTTS(text=text, lang='en')
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp.read()
    except Exception as e:
        print(f"An error occurred during text-to-speech conversion: {e}")
        return None
