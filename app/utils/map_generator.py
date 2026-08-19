import os
import cv2

# Resolve paths relative to project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

IMAGE_PATH = os.path.join(BASE_DIR, "knowledge_base", "svit_drone_campus_map.png")
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "navigation_maps")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

base_image = cv2.imread(IMAGE_PATH)

if base_image is None:
    raise FileNotFoundError(f"❌ Could not find drone map at: {IMAGE_PATH}")

MAIN_ENTRANCE = (500, 1800)

DESTINATIONS = {
    # Departments
    "Computer Engineering Department": [(500, 1800), (600, 1200), (750, 900)],
    "Information Technology Department": [(500, 1800), (600, 1200), (800, 850)],
    "Mechanical Engineering Department": [(500, 1800), (400, 1100), (350, 700)],
    "Civil Engineering Department": [(500, 1800), (400, 1100), (300, 650)],
    "Electrical Engineering Department": [(500, 1800), (600, 1300), (650, 1100)],
    "Electronics & Communication Department": [(500, 1800), (600, 1300), (700, 1150)],
    "Architecture Department": [(500, 1800), (400, 1500), (250, 1400)],
    "Aeronautical Engineering Department": [(500, 1800), (400, 1100), (200, 800)],
    "MCA & BCA Department": [(500, 1800), (600, 1200), (850, 950)],
    
    # Admin Block Destinations
    "Administration Office": [(500, 1800), (550, 1400), (520, 1000)],
    "Central Library": [(500, 1800), (550, 1400), (520, 1000)],
    "Reading Room": [(500, 1800), (550, 1400), (520, 1000)],
    "Book Bank": [(500, 1800), (550, 1400), (520, 1000)],
    "Indoor Sports Room": [(500, 1800), (550, 1400), (520, 1000)],
    "Girls Common Room": [(500, 1800), (550, 1400), (520, 1000)],

    # General Amenities
    "Canteen": [(500, 1800), (700, 1500), (800, 1400)],
    "Stationary": [(500, 1800), (700, 1500), (780, 1420)],
    "Sports Court": [(500, 1800), (300, 1600), (200, 1700)],
    "Bus Stop": [(500, 1800), (480, 1850)],
}

def generate_all_maps():
    for destination_name, path_points in DESTINATIONS.items():
        img = base_image.copy()
        
        # 1. Draw clean white arrows along path
        for i in range(len(path_points) - 1):
            pt1 = path_points[i]
            pt2 = path_points[i+1]
            cv2.arrowedLine(
                img, pt1, pt2, 
                color=(255, 255, 255),
                thickness=8, 
                tipLength=0.05
            )
        
        # 2. Add text overlay
        target_x, target_y = path_points[-1]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.8
        font_color = (255, 255, 255)
        thickness = 4
        text_position = (target_x - 150, target_y - 30)
        
        # Outline for text contrast
        cv2.putText(img, destination_name, text_position, font, font_scale, (0, 0, 0), thickness + 4, cv2.LINE_AA)
        cv2.putText(img, destination_name, text_position, font, font_scale, font_color, thickness, cv2.LINE_AA)
        
        # 3. Save to static/navigation_maps/
        clean_name = destination_name.lower().replace(' ', '_').replace('&', 'and')
        file_name = f"nav_{clean_name}.png"
        save_path = os.path.join(OUTPUT_DIR, file_name)
        
        cv2.imwrite(save_path, img)
        print(f"✅ Generated map: {file_name}")

if __name__ == "__main__":
    generate_all_maps()