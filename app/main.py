import os
import re
import json
import pandas as pd
from collections import defaultdict
from datetime import date
from typing import List, Dict, Any
import random
from pathlib import Path

from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# --- PATH CONFIGURATION (THE FIX) ---
# Get the directory where this main.py file is located (e.g., .../amazon_labor_board/app)
BASE_DIR = Path(__file__).resolve().parent

# Get the project root (one level up from app, e.g., .../amazon_labor_board)
PROJECT_ROOT = BASE_DIR.parent

# Initialize FastAPI app
app = FastAPI(
    title="Amazon Virtual Labor Board",
    description="A dynamic and interactive labor board for the Pack department.",
)

# --- MOUNT STATIC & TEMPLATES ---
# 1. Mount static files (CSS/JS)
# This assumes your 'static' folder is inside 'app' (sibling to main.py)
static_path = BASE_DIR / "static"
# Create static dir if it doesn't exist to prevent crash
static_path.mkdir(parents=True, exist_ok=True) 
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# 2. Initialize Jinja2 templates
# This assumes your 'templates' folder is inside 'app' (sibling to main.py)
templates_path = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# --- DATA CONFIGURATION ---
# Define the data directory and file path
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "labor_board.json"

# Create the data directory automatically if it doesn't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Global data store (in-memory for now)
labor_data = defaultdict(lambda: {'positions': {}, 'top_performers': [], 'total_positions': 0})

# Sample position data
# NOTE: Currently, changes to this structure are NOT saved to disk, only assignments are.
RAW_POSITIONS = {
    "Taper": 8,
    "WaterSpider": 8,
    "Packer": 9,
    "Problem Solve": 2,
    "Process Assistant": 4,
    "Process Guide": 2,
    "Kickout": 3,
    "Jam Clearer": 2,
    "DropZone": 1,
    "Cart Runner": 1,
    "Box On Demand Line 1 - Loader": 1,
    "Box On Demand Line 1 - Operator": 1,
    "Box On Demand Line 1 - Assembler": 2,
    "Box On Demand Line 1 - Slam": 1,
    "Box On Demand Line 2 - Loader": 1,
    "Box On Demand Line 2 - Operator": 1,
    "Box On Demand Line 2 - Assembler": 2,
    "Box On Demand Line 2 - Slam": 1,
    "Gift Wrap": 2,
    "SIOC Slam": 5,
    "Rebin": 3
}

# Helper function to generate a flat list of all positions with unique keys
def create_unique_positions_list(positions_map: Dict[str, int]) -> List[str]:
    """Flattens the positions map into a list of unique keys."""
    unique_positions = []
    for pos_name, count in positions_map.items():
        if count == 1:
            unique_positions.append(pos_name)
        else:
            for i in range(1, count + 1):
                unique_positions.append(f"{pos_name} {i}")
    return unique_positions

# Function to save data to a JSON file
def save_data():
    """Saves the labor_data dictionary to a JSON file."""
    try:
        with open(DATA_FILE, "w") as f:
            # Convert defaultdict to a regular dict for JSON serialization
            json.dump(dict(labor_data), f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

# Function to load data from a JSON file
def load_data():
    """Loads the labor_data dictionary from a JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
                # Convert back to defaultdict
                for k, v in data.items():
                    labor_data[k] = v
            except json.JSONDecodeError:
                print("Warning: Data file is corrupted. Starting with a blank board.")

# Load data when the application starts
load_data()

# Simple Content-Based Recommender (Dummy version for now)
def recommend_associates(date_str: str, position: str) -> List[str]:
    """Recommends associates for a given position on a specific date."""
    if date_str not in labor_data or 'all_associates' not in labor_data[date_str]:
        return []
        
    all_associates = list(labor_data[date_str]['all_associates'])
    random.shuffle(all_associates)
    
    # Get list of currently assigned associates to exclude them
    assigned = [pos for pos in labor_data[date_str]['positions'].values() if pos]
    return [assoc for assoc in all_associates if assoc not in assigned]

# Function to get top performers based on a dummy performance metric
def get_top_performers(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Identifies and returns top performers from the DataFrame."""
    if 'Performance' not in df.columns:
        return []
    high_performers = df[df['Performance'] == 'High'].copy()
    if high_performers.empty:
        return []
        
    # Fixed deprecation warning for count/transform
    # Simply getting unique high performers
    top_performers = high_performers['Associate Name'].unique().tolist()
    random.shuffle(top_performers)
    return [{"name": name} for name in top_performers[:3]]

# Route to handle file uploads
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    """Handles the upload of a CSV or Excel file."""
    # Use the absolute DATA_DIR path
    file_path = DATA_DIR / file.filename
    
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # Determine file type
        if str(file_path).endswith('.csv'):
            df = pd.read_csv(file_path) 
        elif str(file_path).endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path, engine='openpyxl')
        else:
            if file_path.exists():
                os.remove(file_path)
            return {"message": "Error: Unsupported file type. Use CSV or Excel.", "status": "error"}
        
        if df is not None:
            df.columns = [col.strip() for col in df.columns]
            
            required_cols = ['Date', 'Associate Name', 'Performance']
            if not all(col in df.columns for col in required_cols):
                if file_path.exists():
                    os.remove(file_path)
                return {"message": f"Error: Missing required columns: {required_cols}", "status": "error"}

            for date_str, group in df.groupby('Date'):
                # Ensure the date string is formatted correctly if it's a timestamp
                date_key = str(date_str).split(" ")[0] # simpler date format
                
                labor_data[date_key]['all_associates'] = group['Associate Name'].unique().tolist()
                labor_data[date_key]['top_performers'] = get_top_performers(group)
                labor_data[date_key]['positions'] = {key: "" for key in create_unique_positions_list(RAW_POSITIONS)}
            
            # Save the updated data
            save_data()
        
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        print(f"An unexpected error occurred: {e}")
        return {"message": f"An unexpected error occurred: {str(e)}", "status": "error"}

    return {"filename": file.filename, "message": "File processed successfully!", "status": "success"}

# Route for the main labor board page
@app.get("/", response_class=HTMLResponse)
async def get_labor_board(request: Request, date_str: str = str(date.today())):
    """Renders the main labor board page for a given date."""
    
    if date_str not in labor_data:
        # This will now create a fresh list of positions based on the current RAW_POSITIONS
        labor_data[date_str]['positions'] = {key: "" for key in create_unique_positions_list(RAW_POSITIONS)}
        labor_data[date_str]['all_associates'] = []
        labor_data[date_str]['top_performers'] = []
    
    positions = labor_data[date_str]['positions']
    all_associates = labor_data[date_str]['all_associates']
    top_performers = labor_data[date_str]['top_performers']
    
    recommendations = {}
    unique_pos_keys = create_unique_positions_list(RAW_POSITIONS)
    
    for pos_key in unique_pos_keys:
        # Ensure the position key exists in the data (in case RAW_POSITIONS changed)
        if pos_key not in positions:
            positions[pos_key] = ""
        recommendations[pos_key] = recommend_associates(date_str, pos_key)
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "positions": positions,
            "all_associates": all_associates,
            "recommendations": recommendations,
            "current_date": date_str,
            "top_performers": top_performers,
            "raw_positions": RAW_POSITIONS
        }
    )

# Pydantic model for the incoming JSON data
class PositionUpdate(BaseModel):
    position: str
    action: str

# New endpoint to update any position's count
@app.post("/update_position_count/")
async def update_position_count(data: PositionUpdate):
    global RAW_POSITIONS
    
    if data.position in RAW_POSITIONS:
        if data.action == 'add':
            RAW_POSITIONS[data.position] += 1
            # Note: We need to trigger a save or update the logic to persist RAW_POSITIONS
            # For now, this is in-memory only per your original script
        elif data.action == 'remove' and RAW_POSITIONS[data.position] > 1:
            RAW_POSITIONS[data.position] -= 1
            
        return {"message": f"{data.position} count updated to {RAW_POSITIONS[data.position]}."}
    
    return {"message": "Position not found or cannot be removed.", "status": "error"}

# Route to handle updating a position assignment
@app.post("/update_position/")
async def update_position(request: Request):
    form_data = await request.form()
    date_str = form_data.get("date")
    position = form_data.get("position")
    associate = form_data.get("associate")
    
    if date_str and position:
        # Initialize if date doesn't exist
        if date_str not in labor_data:
             labor_data[date_str]['positions'] = {}

        labor_data[date_str]['positions'][position] = associate
        
        # Save the updated data after a change
        save_data()
        return {"status": "success", "message": f"Updated {position} with {associate}"}
    
    return {"status": "error", "message": "Failed to update position"}