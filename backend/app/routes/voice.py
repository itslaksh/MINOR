import speech_recognition as sr
import pyttsx3

def listen_and_transcribe(language="en-US"):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    engine = pyttsx3.init()
    engine.setProperty('rate', 180)

    print("voice assistant is listening... (Say 'exit' to stop)")

    while True:
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                print("🎤 Listening...")
                audio = recognizer.listen(source)

            print("⏳ Recognizing...")
            text = recognizer.recognize_google(audio, language=language)
            print(f"🗣 You said: {text}")

            if text.lower() in ["exit", "quit", "stop"]:
                engine.say("Goodbye!")
                engine.runAndWait()
                break

            response = f"You said: {text}"
            engine.say(response)
            engine.runAndWait()

        except sr.UnknownValueError:
            print("❗ Could not understand audio")
        except sr.RequestError:
            print("⚠️ Could not connect to Google API")

if __name__ == "__main__":
    language = input("Enter language code (e.g., en-US): ").strip() or "en-US"
    listen_and_transcribe(language)
