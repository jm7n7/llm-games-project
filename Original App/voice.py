from google.cloud import texttospeech

def generate_speech(text, output_filename, rate="medium", pitch="+2st", volume="medium", voice_name="en-US-Chirp3-HD-Leda"):
    """
    Generate speech from text using Google Cloud Text-to-Speech API.
    
    Args:
        text: The text to convert to speech
        output_filename: Name of the output MP3 file (e.g., "slide3.mp3")
        rate: Speaking rate - "x-slow", "slow", "medium", "fast", "x-fast" or percentage like "80%"
        pitch: Pitch adjustment - "-5st" to "+5st" (semitones) or percentage like "+10%"
        volume: Volume level - "silent", "x-soft", "soft", "medium", "loud", "x-loud" or decibels like "+6dB"
        voice_name: Voice to use (default: Gemini Pro TTS Leda voice)
    
    Example:
        generate_speech(
            "Hello world!",
            "output.mp3",
            rate="slow",
            pitch="+3st",
            volume="medium"
        )
    """
    client = texttospeech.TextToSpeechClient()
    
    # Create SSML with prosody tags for tone control
    ssml_text = f"""
<speak>
  <prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
    {text}
  </prosody>
</speak>
"""
    
    synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=voice_name
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file "{output_filename}"')


# Example usage - generate slide3.mp3
if __name__ == "__main__":
    text = "Jack is the coolest guy in the world!"
    
    generate_speech(
        text=text,
        output_filename="Jack_Example.mp3",
        rate="slow",
        pitch="+2st",
        volume="medium"
    )
