import io
import base64
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image
import asyncio
import aiohttp

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InferenceRequest(BaseModel):
    model_names: list[str]
    imageUrl: str
    confidenceThreshold: float

async def download_image(session, url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with session.get(url, headers=headers, allow_redirects=True) as response:
        if response.status == 200:
            return await response.read()
        else:
            raise HTTPException(status_code=404, detail="Image not found")

async def process_model(model_name, image, confidence_threshold):
    try:
        model = YOLO(f"weights/{model_name}.pt")
        results = model(image, conf=confidence_threshold)[0]
        
        opencv_image = image.copy()
        for result in results.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = result
            if score > confidence_threshold:
                cv2.rectangle(opencv_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(opencv_image, f"{model.names[int(class_id)]}: {score:.2f}", 
                            (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        _, buffer = cv2.imencode('.jpg', opencv_image)
        processed_img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        detections = [
            {
                "class": model.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox_xyxy": box.xyxy.tolist()[0],
            } for box in results.boxes
        ]
        
        return {
            "model_name": model_name,
            "resultImage": f"data:image/jpeg;base64,{processed_img_base64}",
            "detections": detections,
        }
    except Exception as e:
        return {
            "model_name": model_name,
            "error": str(e)
        }

@app.post("/run_inference")
async def run_inference(request: InferenceRequest):
    try:
        async with aiohttp.ClientSession() as session:
            image_data = await download_image(session, request.imageUrl)
        
        image = Image.open(io.BytesIO(image_data))
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        image_width, image_height = image.size
        
        _, buffer = cv2.imencode('.jpg', opencv_image)
        original_img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        tasks = [process_model(model_name, opencv_image, request.confidenceThreshold) 
                 for model_name in request.model_names]
        
        results = await asyncio.gather(*tasks)
        
        return {
            "originalImage": f"data:image/jpeg;base64,{original_img_base64}",
            "imageWidth": image_width,
            "imageHeight": image_height,
            "modelResults": results
        }

    except Exception as e:
        print("Error: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)