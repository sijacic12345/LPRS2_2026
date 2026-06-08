import cv2
import numpy as np
import os

# ============================================================
# PODEŠAVANJE FOLDERA
# ============================================================
input_folder = 'slike'
output_folder = 'final'
canny_folder = 'canny_cleared'

# Kreiraj foldere ako ne postoje
for folder in [output_folder, canny_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ============================================================
# FUNKCIJA ZA DETEKCIJU LINIJA
# ============================================================
def detect_lines(edges_img, original_img):
    lines = cv2.HoughLinesP(
        edges_img,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=40,
        maxLineGap=20
    )
    
    result = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
    return result

# ============================================================
# GLAVNA PETLJA (0-38)
# ============================================================
for i in range(39):
    filename = f"slika{i}.jpg"
    input_path = os.path.join(input_folder, filename)
    
    if not os.path.exists(input_path):
        continue

    img = cv2.imread(input_path)
    if img is None:
        continue

    print(f"Obrađujem: {filename}...")
    h, w = img.shape[:2]

    # --- KORAK 1: CROP NA DONJU POLOVINU ---
    cropped = img[h//2:h, 0:w]

    # --- KORAK 2: OSNOVNA OBRADA ---
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny detekcija
    median = np.median(blurred)
    sigma = 0.8
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))
    edges = cv2.Canny(blurred, lower, upper)

    # --- KORAK 3: CANNY CLEARED (Morfološko zatvaranje) ---
    # Ovaj korak spaja isprekidane ivice i uklanja sitne mrlje
    kernel = np.ones((3, 3), np.uint8)
    edges_cleared = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    # Sačuvaj očišćeni Canny u poseban folder za proveru
    cv2.imwrite(os.path.join(canny_folder, f"canny{i}.jpg"), edges_cleared)

    # --- KORAK 4: DETEKCIJA LINIJA ---
    # Koristimo edges_cleared za bolji rezultat Hough-a
    final_result = detect_lines(edges_cleared, blurred)

    # --- KORAK 5: ČUVANJE FINALNOG REZULTATA ---
    output_filename = f"slika{i}_final.jpg"
    output_path = os.path.join(output_folder, output_filename)
    cv2.imwrite(output_path, final_result)

print(f"\nGotovo! \nRezultati su u: {output_folder} \nOčišćeni Canny u: {canny_folder}")