import os
import re
import json
import pandas as pd
from collections import defaultdict
from datetime import date
from typing import List, Dict, Any
import random

from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Amazon Virtual Labor Board",
    description="A dynamic and interactive labor board for the Pack department.",
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# File path for saving the labor board data
DATA_FILE = "data/labor_board.json"

# Global data store (in-memory for now)
labor_data = defaultdict(lambda: {'positions': {}, 'top_performers': [], 'total_positions': 0})

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

# Sample position data based on your specifications
# We will use this to generate the keys for our data store
# Make this a global variable so we can modify it
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

# Function to save data to a JSON file
def save_data():
    """Saves the labor_data dictionary to a JSON file."""
    with open(DATA_FILE, "w") as f:
        # Convert defaultdict to a regular dict for JSON serialization
        json.dump(dict(labor_data), f, indent=4)

# Function to load data from a JSON file
def load_data():
    """Loads the labor_data dictionary from a JSON file."""
    if os.path.exists(DATA_FILE):
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
    all_associates = list(labor_data[date_str]['all_associates'])
    random.shuffle(all_associates)
    assigned = [pos for pos in labor_data[date_str]['positions'].values() if pos]
    return [assoc for assoc in all_associates if assoc not in assigned]

# Function to get top performers based on a dummy performance metric
def get_top_performers(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Identifies and returns top performers from the DataFrame."""
    if 'Performance' not in df.columns:
        return []
    high_performers = df[df['Performance'] == 'High'].copy()
    high_performers['count'] = high_performers.groupby('Associate Name')['Associate Name'].transform('count')
    top_performers = high_performers['Associate Name'].unique().tolist()
    random.shuffle(top_performers)
    return [{"name": name} for name in top_performers[:3]]

# Route to handle file uploads
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    """Handles the upload of a CSV or Excel file."""
    file_path = f"data/{file.filename}"
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path, engine='openpyxl')
        
        if df is not None:
            df.columns = [col.strip() for col in df.columns]
            
            required_cols = ['Date', 'Associate Name', 'Performance']
            if not all(col in df.columns for col in required_cols):
                os.remove(file_path)
                return {"message": "Error: Missing required columns.", "status": "error"}

            for date_str, group in df.groupby('Date'):
                labor_data[date_str]['all_associates'] = group['Associate Name'].unique().tolist()
                labor_data[date_str]['top_performers'] = get_top_performers(group)
                labor_data[date_str]['positions'] = {key: "" for key in create_unique_positions_list(RAW_POSITIONS)}
            
            # Save the updated data
            save_data()
        else:
            os.remove(file_path)
            return {"message": "Error: Unsupported file type.", "status": "error"}

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"An unexpected error occurred: {e}")
        return {"message": f"An unexpected error occurred: {e}", "status": "error"}

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
    for pos_key in create_unique_positions_list(RAW_POSITIONS):
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
    
    if data.position in RAW_POSITIONS and RAW_POSITIONS[data.position] > 1:
        if data.action == 'add':
            RAW_POSITIONS[data.position] += 1
        elif data.action == 'remove' and RAW_POSITIONS[data.position] > 1:
            RAW_POSITIONS[data.position] -= 1
        
        # Save the updated data after a change
        save_data()
        
        return {"message": f"{data.position} count updated to {RAW_POSITIONS[data.position]}."}
    
    elif data.position in RAW_POSITIONS and RAW_POSITIONS[data.position] == 1 and data.action == 'add':
        RAW_POSITIONS[data.position] += 1
        save_data()
        return {"message": f"{data.position} count updated to {RAW_POSITIONS[data.position]}."}
    
    return {"message": "Position not found or cannot be removed.", "status": "error"}

# Route to handle updating a position
@app.post("/update_position/")
async def update_position(request: Request):
    form_data = await request.form()
    date_str = form_data.get("date")
    position = form_data.get("position")
    associate = form_data.get("associate")
    
    if date_str and position in labor_data.get(date_str, {}).get("positions", {}):
        labor_data[date_str]['positions'][position] = associate
        # Save the updated data after a change
        save_data()
        return {"status": "success", "message": f"Updated {position} with {associate}"}
    
    return {"status": "error", "message": "Failed to update position"}