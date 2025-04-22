import speech_recognition as sr
import webbrowser
import pyttsx3
import musicLibrary
import requests
from openai import OpenAI
from gtts import gTTS
import pygame
import os
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

# Initialize recognizer and engine
recognizer = sr.Recognizer()
engine = pyttsx3.init()
newsapi = "<Your NewsAPI Key Here>"

# Check required dependencies
try:
    import sounddevice as sd
    from scipy.io.wavfile import write
except ImportError:
    print("Error: Required sound packages not installed")
    print("Run: pip install sounddevice scipy")
    exit(1)

def speak_old(text):
    """Fallback text-to-speech using pyttsx3"""
    engine.say(text)
    engine.runAndWait()

def speak(text):
    """Improved text-to-speech using gTTS and pygame"""
    try:
        tts = gTTS(text=text, lang='en')
        tts.save('temp.mp3')

        pygame.mixer.music.load('temp.mp3')
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Speech error: {e}")
        speak_old(text)  # Fallback
    finally:
        if os.path.exists('temp.mp3'):
            os.remove('temp.mp3')

def record_with_sounddevice(duration=5):
    """Record audio using sounddevice"""
    fs = 44100  # Sample rate
    print("Listening... (Speak now)")
    try:
        recording = sd.rec(int(duration * fs),
                           samplerate=fs,
                           channels=1,
                           dtype='int16')
        sd.wait()
        return fs, recording
    except Exception as e:
        print(f"Recording error: {e}")
        return None, None

def recognize_audio(fs, audio_data):
    """Recognize speech from audio data"""
    if fs is None or audio_data is None:
        return None

    temp_file = "temp_recording.wav"
    try:
        write(temp_file, fs, audio_data)
        with sr.AudioFile(temp_file) as source:
            audio = recognizer.record(source)
            return recognizer.recognize_google(audio).lower()
    except sr.UnknownValueError:
        print("Could not understand audio")
    except Exception as e:
        print(f"Recognition error: {e}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    return None

def aiProcess(command):
    """Process commands with OpenAI"""
    try:
        client = OpenAI(api_key="<Your OpenAI Key Here>")
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Jarvis, a helpful AI assistant. Respond concisely."},
                {"role": "user", "content": command}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"AI error: {e}")
        return "Sorry, I encountered an error"

def processCommand(command):
    """Execute commands based on voice input"""
    if not command:
        return

    command = command.lower()

    # Exit commands
    if any(word in command for word in ["exit", "quit", "stop", "shut down"]):
        speak("Goodbye!")
        pygame.mixer.quit()
        exit()

    # Website commands
    sites = {
        "google": "https://google.com",
        "facebook": "https://facebook.com",
        "youtube": "https://youtube.com",
        "linkedin": "https://linkedin.com"
    }

    for site, url in sites.items():
        if f"open {site}" in command:
            speak(f"Opening {site.capitalize()}")
            webbrowser.open(url)
            return

    # Music commands
    if command.startswith("play"):
        try:
            song = command.split("play")[1].strip()
            if song in musicLibrary.music:
                speak(f"Playing {song}")
                webbrowser.open(musicLibrary.music[song])
            else:
                speak(f"Sorry, I don't know the song {song}")
        except Exception as e:
            print(f"Music error: {e}")
            speak("Could not play music")

    # News command
    elif "news" in command:
        try:
            r = requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={newsapi}")
            if r.status_code == 200:
                articles = r.json().get('articles', [])[:5]  # Limit to 5 articles
                for article in articles:
                    speak(article['title'])
            else:
                speak("Could not fetch news")
        except Exception as e:
            print(f"News error: {e}")
            speak("News service unavailable")

    # Default AI response
    else:
        output = aiProcess(command)
        speak(output)

def main():
    """Main execution loop"""
    pygame.mixer.init()
    speak("Initializing Jarvis...")

    # Check audio backend
    try:
        import pyaudio
        use_pyaudio = True
    except ImportError:
        use_pyaudio = False
        print("PyAudio not found, using sounddevice instead")

    try:
        while True:
            print("\nWaiting for wake word 'jarvis'...")

            try:
                # Listen for wake word
                if use_pyaudio:
                    with sr.Microphone() as source:
                        recognizer.adjust_for_ambient_noise(source)
                        audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
                    word = recognizer.recognize_google(audio)
                else:
                    fs, recording = record_with_sounddevice(duration=2)
                    word = recognize_audio(fs, recording)

                if word and "jarvis" in word:
                    speak("Yes? How may I help you?")

                    # Listen for command
                    if use_pyaudio:
                        with sr.Microphone() as source:
                            audio = recognizer.listen(source, phrase_time_limit=5)
                        command = recognizer.recognize_google(audio)
                    else:
                        fs, recording = record_with_sounddevice(duration=5)
                        command = recognize_audio(fs, recording)

                    if command:
                        print(f"Command: {command}")
                        processCommand(command)

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                speak("I didn't catch that")
            except Exception as e:
                print(f"Error: {e}")
                speak("Sorry, I encountered an error")

    except KeyboardInterrupt:
        speak("Shutting down")
    finally:
        pygame.mixer.quit()
        print("Jarvis shutdown complete")

if __name__ == "__main__":
    main()
