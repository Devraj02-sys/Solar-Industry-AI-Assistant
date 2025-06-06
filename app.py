# -*- coding: utf-8 -*-
"""app.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/#fileId=https%3A//huggingface.co/spaces/Devraj02/solar-analyzer/blob/main/app.ipynb
"""
import subprocess

subprocess.run(["pip", "install", "ultralytics", "gradio", "openai", "--quiet"])


pip install ultralytics gradio openai --quiet

from ultralytics import YOLO
import cv2
from PIL import Image
import numpy as np

model = YOLO("yolov8n-seg.pt")  # Lightweight segmentation model

def analyze_rooftop(image):
    results = model(image)
    result_img = results[0].plot()  # Image with segmentation overlay
    return Image.fromarray(result_img)

def estimate_solar_potential(area_m2):
    panel_efficiency = 0.18
    irradiance = 5.5  # kWh/m²/day
    panel_power = panel_efficiency * irradiance * area_m2  # daily output in kWh
    annual_energy = panel_power * 365  # annual output

    cost_per_watt = 50  # ₹/W
    total_power_kw = annual_energy / 365 / 5  # approximate kW system size
    installation_cost = total_power_kw * 1000 * cost_per_watt

    savings_per_year = annual_energy * 8  # ₹8 per kWh
    roi_years = installation_cost / savings_per_year

    return {
        "Usable Area (m²)": round(area_m2, 2),
        "Estimated System Size (kW)": round(total_power_kw, 2),
        "Annual Output (kWh)": round(annual_energy, 2),
        "Estimated Installation Cost (₹)": round(installation_cost, 2),
        "Estimated Savings/Year (₹)": round(savings_per_year, 2),
        "Estimated Payback Period (years)": round(roi_years, 2)
    }

def mock_solar_analysis(image, area_estimate_m2):
    result = analyze_rooftop(image)
    roi = estimate_solar_potential(area_estimate_m2)
    return result, roi

import  gradio as gr
gr.Interface(
    fn=mock_solar_analysis,
    inputs=[
        gr.Image(type="filepath", label="Upload Rooftop Image"),
        gr.Slider(10, 200, step=5, label="Estimated Rooftop Area (m²)")
    ],
    outputs=[
        gr.Image(label="Rooftop Detection"),
        gr.JSON(label="Solar Analysis Report")
    ],
    title="AI-Powered Rooftop Solar Analyzer"
).launch()

def get_rooftop_area_from_mask(results, pixels_per_meter=50):
    """
    Estimate rooftop area from segmentation mask.
    pixels_per_meter: assumed scale, 50px ~ 1 meter (adjust as needed)
    """
    mask = results[0].masks.data[0].cpu().numpy()  # get the first mask
    area_pixels = np.sum(mask)
    area_m2 = area_pixels / (pixels_per_meter ** 2)
    return area_m2

def full_rooftop_analysis(image):
    results = model(image)
    result_img = results[0].plot()

    try:
        area_m2 = get_rooftop_area_from_mask(results)
    except Exception as e:
        return Image.fromarray(result_img), {"error": f"Rooftop not detected or mask failed: {e}"}

    report = estimate_solar_potential(area_m2)
    return Image.fromarray(result_img), report

gr.Interface(
    fn=full_rooftop_analysis,
    inputs=gr.Image(type="filepath", label="Upload Rooftop Image"),
    outputs=[
        gr.Image(label="Rooftop Detection"),
        gr.JSON(label="Solar Analysis Report")
    ],
    title="AI-Powered Rooftop Solar Analyzer (Auto Area Detection)"
).launch()

pip install transformers accelerate --quiet

from transformers import pipeline

generator = pipeline("text-generation", model="TinyLlama/TinyLlama-1.1B-Chat-v1.0")

def offline_llm_summary(roi_dict):
    prompt = f"""
You are a smart assistant for solar energy advice.

A user has uploaded a satellite image of their rooftop. Based on the analysis, generate a short, clear, and friendly report describing the rooftop's solar installation potential. Include insights on the system size, energy output, installation cost, savings, and the return on investment.

Use this data:
- Rooftop Area: {roi_dict['Usable Area (m²)']} m²
- Estimated System Size: {roi_dict['Estimated System Size (kW)']} kW
- Annual Output: {roi_dict['Annual Output (kWh)']} kWh
- Installation Cost: ₹{roi_dict['Estimated Installation Cost (₹)']}
- Yearly Savings: ₹{roi_dict['Estimated Savings/Year (₹)']}
- Payback Period: {roi_dict['Estimated Payback Period (years)']} years

Keep it under 100 words and encourage solar adoption if feasible.
Response:
"""
    output = generator(prompt, max_new_tokens=120, temperature=0.7)[0]["generated_text"]
    return output.split("Response:")[-1].strip()

def full_rooftop_analysis_with_local_llm(image):
    results = model(image)
    result_img = results[0].plot()

    try:
        area_m2 = get_rooftop_area_from_mask(results)
        report = estimate_solar_potential(area_m2)
        summary = offline_llm_summary(report)
        return Image.fromarray(result_img), report, summary
    except Exception as e:
        return Image.fromarray(result_img), {"error": str(e)}, "LLM summary failed."

gr.Interface(
    fn=full_rooftop_analysis_with_local_llm,
    inputs=gr.Image(type="filepath", label="Upload Rooftop Image"),
    outputs=[
        gr.Image(label="Rooftop Detection"),
        gr.JSON(label="Solar Analysis Report"),
        gr.Textbox(label="LLM Summary (Offline)")
    ],
    title="AI Rooftop Solar Analyzer (Offline LLM)"
).launch()

pip install git+https://github.com/facebookresearch/segment-anything.git
pip install opencv-python matplotlib --quiet

import os

# Create directory and download the model
os.makedirs("sam_weights", exist_ok=True)

wget -O sam_weights/sam_vit_h.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
import torch
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Load SAM
sam = sam_model_registry["vit_h"](checkpoint="sam_weights/sam_vit_h.pth")
sam.to("cuda")

# Mask generator
mask_generator = SamAutomaticMaskGenerator(sam)

def segment_rooftop_with_sam(image_path):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    masks = mask_generator.generate(image_rgb)

    # Combine all SAM masks into one binary mask
    combined_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for mask in masks:
        combined_mask = np.logical_or(combined_mask, mask["segmentation"])

    combined_mask = combined_mask.astype(np.uint8)

    # Create colored overlay on the image
    overlay = image_rgb.copy()
    overlay[combined_mask == 1] = [0, 255, 0]  # green mask for rooftop

    # Blend original + mask for visibility
    alpha = 0.5
    blended = cv2.addWeighted(image_rgb, 1 - alpha, overlay, alpha, 0)

    # Return visual + mask area (pixel count)
    return Image.fromarray(blended), np.sum(combined_mask)

def area_from_sam_mask(pixel_count, pixels_per_meter=50):
    return pixel_count / (pixels_per_meter ** 2)

def full_rooftop_analysis_with_sam(image_path):
    masked_image, pixel_count = segment_rooftop_with_sam(image_path)
    area_m2 = area_from_sam_mask(pixel_count)
    report = estimate_solar_potential(area_m2)
    summary = offline_llm_summary(report)

    return masked_image, report, summary

gr.Interface(
    fn=full_rooftop_analysis_with_sam,
    inputs=gr.Image(type="filepath", label="Upload Satellite Rooftop Image"),
    outputs=[
        gr.Image(label="Rooftop Segmentation (SAM)"),
        gr.JSON(label="Solar Analysis Report"),
        gr.Textbox(label="LLM Summary (Offline)")
    ],
    title="SAM-Powered Rooftop Solar Analyzer"
).launch()

def segment_rooftop_with_clean_overlay(image_path):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    masks = mask_generator.generate(image_rgb)

    # Filter + sort largest masks
    masks = sorted(masks, key=lambda x: np.sum(x["segmentation"]), reverse=True)
    masks = [m for m in masks if np.sum(m["segmentation"]) > 500][:30]  # max 30 big masks

    annotated_img = image_rgb.copy()
    total_px = 0

    for mask in masks:
        seg = mask['segmentation'].astype(np.uint8)
        area_px = np.sum(seg)
        total_px += area_px

        overlay = np.zeros_like(image_rgb)
        overlay[seg == 1] = (0, 255, 255)

        annotated_img = cv2.addWeighted(annotated_img, 1, overlay, 0.4, 0)

        x, y, w, h = cv2.boundingRect(seg)
        area_m2 = area_px / (50 ** 2)
        cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (255, 255, 255), 1)
        cv2.putText(annotated_img, f"{area_m2:.2f} m²", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    return Image.fromarray(annotated_img), total_px

def full_rooftop_analysis_with_visual_overlay(image_path):
    annotated_img, total_px = segment_rooftop_with_clean_overlay(image_path)
    area_m2 = area_from_sam_mask(total_px)
    report = estimate_solar_potential(area_m2)
    summary = offline_llm_summary(report)

    return annotated_img, report, summary

demo=gr.Interface(
    fn=full_rooftop_analysis_with_visual_overlay,
    inputs=gr.Image(type="filepath", label="Upload Satellite Image"),
    outputs=[
        gr.Image(label="Rooftop Detection + Area"),
        gr.JSON(label="Solar Report"),
        gr.Textbox(label="LLM Summary")
    ],
    title="Solar Analyzer with Visual Area Overlay"
)
if __name__ == "__main__":
    demo.launch(share=True)

pip install reportlab

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_simple_pdf(report_data, summary_text, output_path="solar_report_simple.pdf"):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    x, y = 50, height - 50

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "🌞 Rooftop Solar Installation Report")
    y -= 40

    # Solar Report Data
    c.setFont("Helvetica", 12)
    for key, value in report_data.items():
        c.drawString(x, y, f"{key}: {value}")
        y -= 20

    # AI Summary
    y -= 20
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, y, "🧠 AI Summary:")
    y -= 20

    c.setFont("Helvetica-Oblique", 11)
    for line in summary_text.split('\n'):
        c.drawString(x, y, line.strip())
        y -= 15

    c.setFont("Helvetica", 9)
    y = 40
    c.drawString(x, y, "Generated by Devraj Singh – Internship Project, 2025")
    c.save()

# Sample data (use your actual results)
report_dict = {
    "Usable Area (m²)": "43.36",
    "Estimated System Size (kW)": "8.58",
    "Annual Output (kWh)": "15667.56",
    "Installation Cost (₹)": "429248.16",
    "Estimated Savings/Year (₹)": "125340.46",
    "Payback Period (years)": "3.42"
}

llm_summary = (
    "Your rooftop can support an 8.58 kW solar system, producing approx. 15,667 kWh annually.\n"
    "With a cost of ₹4.29L, you'll save over ₹1.25L every year.\n"
    "The system pays for itself in just 3.4 years—a smart green investment!"
)

generate_simple_pdf(report_dict, llm_summary)
