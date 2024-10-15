import os
import numpy as np
import sounddevice as sd
import openai
import datetime
import wavio
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# IBM Watson setup for TTS
IBM_TTS_API_KEY = '"Replace with Key"'
IBM_TTS_URL = 'https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/d97ad15a-a7ac-44a3-b2f4-f21b5fc10002'

tts_authenticator = IAMAuthenticator(IBM_TTS_API_KEY)
text_to_speech = TextToSpeechV1(authenticator=tts_authenticator)
text_to_speech.set_service_url(IBM_TTS_URL)

OPENAI_API_KEY = os.environ.get("Replace_With_Key")  #replace with key
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
openai.api_key = OPENAI_API_KEY
WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"

def record_audio(filename='audio.wav', seconds=10):
    print("Recording...")
    samplerate = 44100
    sd.default.device = 0
    mydata = sd.rec(int(samplerate * seconds), samplerate=samplerate, channels=1, dtype=np.int16)
    sd.wait()
    wavio.write(filename, mydata, samplerate)

def get_openai_response(messages):
    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 50  # Limit to 50 tokens
    }
    response = openai.ChatCompletion.create(**data)
    if response.choices:
        return response.choices[0].message['content'].strip()
    else:
        print("Error from OpenAI API:", response.get('error', 'Unknown error'))
        return ""


def transcribe_audio_with_whisper(filename):
    with open(filename, 'rb') as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

        # If the response contains a 'data' key and inside that a 'text' key
        if 'data' in transcript and 'text' in transcript['data']:
            return transcript['data']['text']
        # If the response contains a 'text' key at the top level
        elif 'text' in transcript:
            return transcript['text']
        # Print the response to diagnose further if needed
        else:
            print("Unexpected structure:", transcript)
            return ""

def main():
    conversation_messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": ""},
        {"role": "assistant", "content": ""}
    ]

    for _ in range(6):
        transcript_filename = 'transcript.txt'
        with open(transcript_filename, 'w') as transcript_file:  # Open the transcript file for writing
            for _ in range(6):
                openai_response = get_openai_response(conversation_messages)
                # Write AI's response to the transcript
                transcript_file.write(f"AI: {openai_response}\n")

                # Synthesize and save AI's audio response
                audio_response = text_to_speech.synthesize(openai_response, accept='audio/wav',
                                                           voice="es-ES_EnriqueV3Voice").get_result().content

                current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                response_filename = f'response_{current_time}.wav'

                with open(response_filename, 'wb') as audio_file:
                    audio_file.write(audio_response)

                os.system(f'open {response_filename}')  # For macOS

                # Check for manual stop command
                stop_recording = input("Type 'stop' to end the recording or press Enter to continue: ")
                if stop_recording.lower() == 'stop':
                    print("Recording stopped by user.")
                    break  # Exit the loop

                # Prompt user to record their response
                input("Press Enter when ready to record your response...")
                record_audio('audio.wav', 10)

                # Write user's response to the transcript
                student_response = transcribe_audio_with_whisper('audio.wav')
                transcript_file.write(f"User: {student_response.strip()}\n")

                # Update conversation messages for the next iteration
                conversation_messages.append({"role": "user", "content": student_response.strip()})
                conversation_messages.append({"role": "assistant", "content": openai_response})
                print("You said:", student_response)

            # Get and process feedback
            feedback = get_openai_response(conversation_messages)
            transcript_file.write(f"Feedback: {feedback}\n")
            feedback_filename = f'feedback_{current_time}.wav'
            audio_feedback = text_to_speech.synthesize(feedback, accept='audio/wav',
                                                       voice="es-ES_EnriqueV3Voice").get_result().content
            with open(feedback_filename, 'wb') as audio_file:
                audio_file.write(audio_feedback)

            os.system(f'open {feedback_filename}')

if name == "main":
    main()