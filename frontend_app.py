
import streamlit as st
import os
import base64
import requests
import numpy as np
import torch
import cv2
from ultralytics import YOLO
from PIL import Image
import io
import re
import json

# Load YOLO model once at startup
yolo_model = YOLO('yolov8n.pt')

# Environment variables for API keys
HF_TOKEN = os.environ.get("HF_TOKEN")
FACEPP_KEY = os.environ.get("FACEPP_KEY")
FACEPP_SECRET = os.environ.get("FACEPP_SECRET")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")

st.title("🪞 LifeMirror: See Your Real Vibe")
st.write("Upload a selfie, voice note, or your Instagram bio to get a brutally honest vibe check!")

# Helper functions from lifemirror_api.py
def get_image_caption(image_bytes):
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    payload = {"model": "Salesforce/blip-image-captioning-base", "inputs": b64}
    response = requests.post(
        "https://api-inference.huggingface.co/pipeline/image-to-text",
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
        json=payload
    )
    if response.status_code != 200:
        print(f"BLIP error {response.status_code}: {response.text}")
        return f"Error: BLIP returned {response.status_code}."
    try:
        data = response.json()
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"]
        else:
            print(f"BLIP unexpected payload: {data}")
            return "Error: BLIP response format unexpected."
    except ValueError:
        print(f"BLIP non-JSON response: {response.text}")
        return "Error: BLIP returned a non-JSON response."

def get_face_attributes(image_bytes):
    response = requests.post(
        "https://api-us.faceplusplus.com/facepp/v3/detect",
        data={"api_key": FACEPP_KEY, "api_secret": FACEPP_SECRET, "return_attributes": "age,gender,emotion,beauty"},
        files={"image_file": image_bytes}
    )
    try:
        return response.json()
    except ValueError:
        print(f"Face++ non-JSON response: {response.text}")
        return {"error": f"Face++ returned non-JSON (status {response.status_code})"}

def get_fashion_tags(image_bytes, candidate_labels=None):
    if candidate_labels is None:
        candidate_labels = ["dress", "jacket", "tshirt", "jeans", "shoes", "hat", "handbag", "scarf", "sunglasses", "watch"]
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    payload = {
        "model": "openai/clip-vit-base-patch32",
        "inputs": b64,
        "parameters": {"candidate_labels": candidate_labels, "multi_label": True}
    }
    response = requests.post(
        "https://api-inference.huggingface.co/pipeline/zero-shot-image-classification",
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
        json=payload
    )
    if response.status_code != 200:
        print(f"FashionCLIP error {response.status_code}: {response.text}")
        return {"error": f"CLIP returned {response.status_code}"}
    try:
        data = response.json()
        if "labels" in data and "scores" in data:
            return list(zip(data["labels"], data["scores"]))
        else:
            print(f"FashionCLIP unexpected payload: {data}")
            return {"error": "Unexpected CLIP format"}
    except ValueError:
        print(f"FashionCLIP non-JSON response: {response.text}")
        return {"error": "Non-JSON from CLIP"}

def get_voice_transcript(audio_bytes):
    response = requests.post(
        "https://api-inference.huggingface.co/models/openai/whisper-1",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        files={"file": audio_bytes}
    )
    if response.status_code != 200:
        print(f"Whisper error {response.status_code}: {response.text}")
        return "Error: Whisper failed."
    try:
        return response.json().get('text', '')
    except ValueError:
        print(f"Whisper non-JSON response: {response.text}")
        return "Error: Whisper returned non-JSON."

def get_vibe_analysis(prompt):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json={"model": "mistralai/mistral-7b-instruct", "messages": [{"role": "user", "content": prompt}]}
    )
    if response.status_code != 200:
        print(f"OpenRouter error {response.status_code}: {response.text}")
        return "Error: Vibe analysis failed."
    try:
        return response.json()['choices'][0]['message']['content']
    except (ValueError, KeyError):
        print(f"OpenRouter unexpected payload: {response.text}")
        return "Error: Vibe response format unexpected."

def rate_face(face_attrs):
    if not face_attrs or "faces" not in face_attrs or not face_attrs["faces"]:
        return {"error": "No face detected."}
    face = face_attrs["faces"][0]["attributes"]
    beauty = face.get("beauty", {})
    emotion = face.get("emotion", {})
    age = face.get("age", {}).get("value", "Unknown")
    gender = face.get("gender", {}).get("value", "Unknown")
    attract = (beauty.get("male_score", 0) + beauty.get("female_score", 0)) / 2
    smile = emotion.get("happiness", 0)
    confidence = smile - (emotion.get("fear", 0) + emotion.get("sadness", 0) + emotion.get("anger", 0))
    dominant_emotion = max(emotion, key=emotion.get) if emotion else "Unknown"
    summary = (
        f"Age: {age}, Gender: {gender}, "
        f"Attractiveness: {attract:.1f}/100, "
        f"Smile: {smile:.1f}/100, "
        f"Confidence: {confidence:.1f}/100, "
        f"Dominant Emotion: {dominant_emotion.capitalize()}"
    )
    return {
        "age": age,
        "gender": gender,
        "attractiveness": round(attract, 1),
        "smile": round(smile, 1),
        "confidence": round(confidence, 1),
        "dominant_emotion": dominant_emotion,
        "summary": summary
    }

def rate_personality(face_attrs):
    if not face_attrs or "faces" not in face_attrs or not face_attrs["faces"]:
        return {"error": "No face detected."}
    emotion = face_attrs["faces"][0]["attributes"].get("emotion", {})
    if not emotion:
        return {"error": "No emotion data."}
    if emotion.get("happiness", 0) > 70:
        return {"personality": "Optimist", "description": "Radiates positivity and joy. People feel good around you!"}
    elif emotion.get("anger", 0) > 30:
        return {"personality": "Fiery", "description": "Passionate and energetic, but sometimes a bit intense."}
    elif emotion.get("sadness", 0) > 30:
        return {"personality": "Sensitive", "description": "Empathetic and thoughtful, you feel things deeply."}
    elif emotion.get("fear", 0) > 30:
        return {"personality": "Cautious", "description": "Careful and observant, you think before you leap."}
    elif emotion.get("surprise", 0) > 30:
        return {"personality": "Adventurous", "description": "You love new experiences and surprises!"}
    else:
        return {"personality": "Balanced", "description": "Calm, collected, and steady. People trust your vibe."}

def try_parse_fashion_json(content):
    try:
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = content[start:end]
            return json.loads(json_str)
    except Exception:
        pass
    def extract_field(field):
        pattern = rf'"{field}"\s*:\s*(.*?)(,|\n|$)'
        match = re.search(pattern, content)
        if match:
            value = match.group(1).strip().strip('"')
            return value
        return ""
    return {
        "outfit_rating": extract_field("outfit_rating"),
        "items": extract_field("items"),
        "good": extract_field("good"),
        "bad": extract_field("bad"),
        "improvements": extract_field("improvements"),
        "overall_style": extract_field("overall_style"),
        "roast": extract_field("roast"),
        "error": "Used fallback parser due to invalid JSON."
    }

def analyze_fashion_llama3(image_bytes):
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    prompt = (
        "You are a brutally honest, witty fashion critic. "
        "Given this image, analyze the person's outfit and overall look. "
        "Respond in this exact JSON format:\n"
        "{\n"
        " \"outfit_rating\": <number 1-10>,\n"
        " \"summary\": <one-sentence summary>,\n"
        " \"pros\": <what's good about the outfit>,\n"
        " \"cons\": <what's bad or could be improved>,\n"
        " \"roast\": <short, funny, tweet-sized roast>\n"
        "}\n"
        "Be concise, honest, and never add extra text outside the JSON."
    )
    payload = {
        "model": "meta-llama/llama-3.2-11b-vision-instruct:free",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image", "image": b64}]}]
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json=payload
    )
    if response.status_code != 200:
        print(f"Llama-3 Vision error {response.status_code}: {response.text}")
        return {"error": "Fashion analysis failed."}
    try:
        content = response.json()['choices'][0]['message']['content']
        result = try_parse_fashion_json(content)
        return result
    except Exception as e:
        print(f"Llama-3 Vision unexpected payload: {response.text}")
        return {"error": "Fashion analysis response format unexpected."}

def detect_fashion_yolov8(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    results = yolo_model(image)
    items = []
    for r in results:
        for c in r.boxes.cls:
            label = yolo_model.names[int(c)]
            items.append(label)
    return list(set(items))

def analyze_fashion_llama3_with_items(image_bytes, detected_items):
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    prompt = (
        f"You are a world-class fashion designer and critic. The following clothing items were detected in the image: {detected_items}. "
        "For each item, say specifically what is good and what is bad about it, as a professional would. "
        "Then, rate the overall outfit from 1-10 as a fashion expert would, suggest concrete ways to improve the outfit (e.g., color, fit, accessories, layering, shoes, etc.). "
        "Summarize the overall style and give a clear, actionable tip to uplift the look. "
        "Respond in this exact JSON format:\n"
        "{\n"
        " \"outfit_rating\": <1-10>,\n"
        " \"items\": [ ... ],\n"
        " \"good\": {<item>: <what's good>, ...},\n"
        " \"bad\": {<item>: <what's bad>, ...},\n"
        " \"improvements\": <specific suggestions>,\n"
        " \"overall_style\": <summary>,\n"
        " \"roast\": <short, funny, tweet-sized roast>\n"
        "}\n"
        "Be specific, honest, and never add extra text outside the JSON."
    )
    payload = {
        "model": "meta-llama/llama-3.2-11b-vision-instruct:free",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image", "image": b64}]}]
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json=payload
    )
    if response.status_code != 200:
        print(f"Llama-3 Vision error {response.status_code}: {response.text}")
        return {"error": "Fashion analysis failed."}
    try:
        content = response.json()['choices'][0]['message']['content']
        result = try_parse_fashion_json(content)
        return result
    except Exception as e:
        print(f"Llama-3 Vision unexpected payload: {response.text}")
        return {"error": "Fashion analysis response format unexpected."}

# Selfie analysis
st.header("1. Selfie Vibe Check")
selfie = st.file_uploader("Upload a selfie photo", type=["jpg", "jpeg", "png"], key="selfie")

if st.button("Analyze Selfie") and selfie:
    files = {"image": selfie.getvalue()}
    with st.spinner("Analyzing your selfie..."):
        caption = get_image_caption(selfie.getvalue())
        face_attrs = get_face_attributes(selfie.getvalue())
        face_rating = rate_face(face_attrs)
        personality_rating = rate_personality(face_attrs)
        detected_items = detect_fashion_yolov8(selfie.getvalue())
        fashion_rating = analyze_fashion_llama3_with_items(selfie.getvalue(), detected_items)
        prompt = (
            f"Image caption: '{caption}'.\n"
            f"Face attributes: {face_attrs}.\n"
            f"Fashion rating: {fashion_rating}.\n"
            "Give a brutally honest, funny, and insightful 'vibe check' as if you were a sarcastic social media influencer."
        )
        vibe = get_vibe_analysis(prompt)
        st.subheader("Vibe:")
        st.write(vibe)
        st.subheader("Image Caption:")
        st.write(caption)
        st.subheader("Face Attributes:")
        st.json(face_attrs)
        if "face_rating" in face_rating and face_rating["face_rating"] != {"error": "No face detected."}:
            st.subheader("Face Rating:")
            st.write(face_rating.get("summary", ""))
            st.json({k: v for k, v in face_rating.items() if k != "summary"})
        if "personality_rating" in personality_rating and personality_rating["personality_rating"] != {"error": "No face detected."}:
            st.subheader("Personality Rating:")
            st.write(personality_rating.get("personality", ""))
            st.write(personality_rating.get("description", ""))
        if "detected_items" in locals():
            st.subheader("Detected Clothing Items:")
            st.write(", ".join(detected_items))
        if "fashion_rating" in locals() and fashion_rating != {"error": "Fashion analysis failed."}:
            fr = fashion_rating
            st.subheader("Fashion Analysis (by Designer):")
            if isinstance(fr, dict):
                st.write(f"**Items:** {fr.get('items', '')}")
                st.write("**What's Good:**")
                st.json(fr.get('good', {}))
                st.write("**What Needs Fixing:**")
                st.json(fr.get('bad', {}))
                st.write("**Improvements:**")
                st.write(fr.get('improvements', ''))
                st.write("**Overall Style:**")
                st.write(fr.get('overall_style', ''))
                st.write("**Roast:**")
                st.write(fr.get('roast', ''))
            else:
                st.write(fr)
        else:
            st.error("Error: " + str(face_attrs if "error" in face_attrs else fashion_rating))

# Voice analysis
st.header("2. Voice Vibe Check")
audio = st.file_uploader("Upload a voice note (wav/mp3)", type=["wav", "mp3", "m4a"], key="audio")

if st.button("Analyze Voice") and audio:
    with st.spinner("Analyzing your voice..."):
        transcript = get_voice_transcript(audio.getvalue())
        prompt = (
            f"Voice transcript: '{transcript}'.\n"
            "Analyze the tone, speed, and confidence. Give a brutally honest, funny, and insightful 'vibe check' as if you were a sarcastic social media influencer."
        )
        vibe = get_vibe_analysis(prompt)
        st.subheader("Vibe:")
        st.write(vibe)
        st.subheader("Transcript:")
        st.write(transcript)
    if not vibe.startswith("Error"):
        st.success("Analysis complete!")
    else:
        st.error("Error: " + vibe)

# Bio analysis
st.header("3. Instagram Bio Vibe Check")
bio = st.text_area("Paste your Instagram bio here")

if st.button("Analyze Bio") and bio:
    with st.spinner("Analyzing your bio..."):
        prompt = (
            f"Instagram bio: '{bio}'.\n"
            "Give a brutally honest, funny, and insightful 'vibe check' as if you were a sarcastic social media influencer."
        )
        vibe = get_vibe_analysis(prompt)
        st.subheader("Vibe:")
        st.write(vibe)
    if not vibe.startswith("Error"):
        st.success("Analysis complete!")
    else:
        st.error("Error: " + vibe)
