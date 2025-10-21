import speech_recognition as sr
import io
from pydub import AudioSegment

def transcribe_audio(audio_bytes):
    """
    Transcribes spoken audio from raw bytes into text using Google's Speech Recognition.
    Includes ambient noise adjustment for better accuracy.
    """
    recognizer = sr.Recognizer()
    try:
        # The audio from streamlit-mic-recorder is already in a compatible format (like WAV)
        # We can load it directly into an audio segment.
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Export as a WAV file in memory for the SpeechRecognition library
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)

        with sr.AudioFile(wav_io) as source:
            # --- NEW: Adjust for ambient noise ---
            # This listens for 1 second to calibrate the recognizer's energy threshold.
            recognizer.adjust_for_ambient_noise(source, duration=1)
            
            audio_data = recognizer.record(source)

        # Recognize speech using Google's free web API
        text = recognizer.recognize_google(audio_data)
        return text
        
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        # This will often catch errors from pydub if FFmpeg is not installed
        print(f"An error occurred during audio transcription: {e}")
        print("Ensure FFmpeg is installed on your system.")
        return None

def text_to_speech(text):
    """
    Converts a string of text into playable audio bytes using Google Text-to-Speech.
    """
    from gtts import gTTS
    try:
        tts = gTTS(text=text, lang='en')
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp.read()
    except Exception as e:
        print(f"An error occurred during text-to-speech conversion: {e}")
        return None

