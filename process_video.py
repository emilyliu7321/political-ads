from google.cloud import speech_v1
from google.cloud.speech_v1 import enums
import io
from pydub import AudioSegment
import os
from google.cloud.speech import types
import wave
from google.cloud import storage
import requests
import subprocess
import urllib.request
import pandas as pd

# FUNCTIONS FOR AUDIO PROCESSING

# Convert .wmv file to .wav
def convert_audio(filename):
    command = "ffmpeg -i " +filename+ " " + filename[:-4] + ".wav"
    subprocess.call(command, shell=True)
    new_name = filename[:-4] + ".wav"
    return new_name

def stereo_to_mono(audio_file_name):
    sound = AudioSegment.from_wav(audio_file_name)
    sound = sound.set_channels(1)
    sound.export(audio_file_name, format="wav")

def sample_recognize(local_file_path):
    """
    Transcribe a short audio file using synchronous speech recognition
    Args:
      local_file_path Path to local audio file, e.g. /path/audio.wav
    """
    client = speech_v1.SpeechClient()
    language_code = "en-US" # The language of the supplied audio
    audio_channel_count = 2
    # Encoding of audio data sent. This sample sets this explicitly.
    # This field is optional for FLAC and WAV audio formats.
    encoding = enums.RecognitionConfig.AudioEncoding.LINEAR16
    config = {
        "language_code": language_code,
        # "sample_rate_hertz": sample_rate_hertz,
        "encoding": encoding,
    }
    with io.open(local_file_path, "rb") as f:
        content = f.read()
    audio = {"content": content}
    response = client.recognize(config, audio)
    claims = []
    for result in response.results:
        # First alternative is the most probable result
        alternative = result.alternatives[0]
        claims.append(alternative.transcript)
        # print(u"Transcript: {}".format(alternative.transcript))
    return claims

# FUNCTIONS FOR CLAIMS

def get_claimbuster_scores(tv_claims):
    """ Submits a list of statements to the Claimbuster API
        and return a list of scored claims"""
    if not tv_claims:
        print('No claims here')
        return
    final_claims_list = []
    print("Processing {} tv claims".format(len(tv_claims)))

    buster_base = 'https://idir.uta.edu/factchecker/score_text/'

    for num, claim in enumerate(tv_claims):
        if num and not num % 50:
            print('Processing claim #{}'.format(num))
        link = 'https://idir.uta.edu/factchecker/score_text/' + claim
        claimbuster_return = requests.get(link).json()['results']
        for score_result in claimbuster_return:
            scored_claim = {
                "claim": claim,
                "score": score_result["score"],
            }
            final_claims_list.append(scored_claim)
    return final_claims_list

def get_claims(wmv): #wmv is a .wmv file
    new_name = convert_audio(wmv)
    stereo_to_mono(new_name)
    claims = sample_recognize(new_name)
    scored_claims = get_claimbuster_scores(claims)
    return scored_claims

def download_video(url): #url is the download link
    file_name = url.rsplit('/', 1)[-1] #Get file name
    try:
        urllib.request.urlretrieve(url, file_name)
    except:
        pass

# Get claims from a remote video
def get_claims_from_url(url):
    download_video(url)
    name = url.rsplit('/', 1)[-1]
    claims = get_claims(name)
    return claims

#FUNCTIONS FOR SPREADSHEET PROCESSING

def get_claims_from_spreadsheet(ads):
    processed_videos = []
    all_claims = []
    for ad in ads:
        name = ad[0]
        url = ad[1]
        sponsor = ad[2]
        if url not in processed_videos:
            claims = [ad] #The first result of the array gives you info about the ad
            claims.append(get_claims_from_url(url))
            all_claims.append(claims)
            processed_videos.append(url)
    return all_claims

def open_spreadsheet(filename):
    unique_data = []
    unique_links = []
    spreadsheet = pd.read_csv(filename)
    for index, row in spreadsheet.iterrows():
        link = row['LINK']
        if link not in unique_links:
            unique_links.append(link)
            element = [row['CREATIVE'], row['LINK'], row['SPONSOR']]
            unique_data.append(element)
    return unique_data

def open_folder(foldername):
    unique_data = []
    for filename in os.listdir(foldername):
        # print(filename)
        location = os.path.join(foldername, filename)
        data = open_spreadsheet(location)
        for item in data:
            if item not in unique_data:
                unique_data.append(item)
    return(unique_data)

# Given a folder of spreadsheets, find all unique advertisements from every spreadsheet
unique_data = open_folder('data')
print(unique_data)
result = get_claims_from_spreadsheet(unique_data)
print(result)
