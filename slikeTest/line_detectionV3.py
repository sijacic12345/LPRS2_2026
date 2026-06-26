import cv2
import numpy as np
import os

"""
POKRETANJE OKRUZENJA:
source ~/cv_env/bin/activate
python3 line_detectionV3.py
"""

# --- PODEŠAVANJA ---
input_folder   = 'Slike2'
output_folder  = 'final'
canny_folder   = 'canny_cleared'
heatmap_folder = 'heatmap'

for folder in [output_folder, canny_folder, heatmap_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- KONSTANTE ---
MIN_AREA                = 200
MAX_TAPE_WIDTH          = 80
MIN_TAPE_WIDTH          = 5
MIN_ASPECT              = 2.5
MIN_LENGTH              = 60
MAX_ANGLE_FROM_VERTICAL = 70

# --- FUNKCIJE ---
def get_average_rect(rect_list):
    if not rect_list:
        return None
    cx = sum(r[0][0] for r in rect_list) / len(rect_list)
    cy = sum(r[0][1] for r in rect_list) / len(rect_list)
    return (cx, cy)

def draw_tape_contours(result, left, right, h):
    w = result.shape[1]
    img_center_x = w // 2
    cv2.line(result, (img_center_x, h), (img_center_x, 0), (0, 0, 255), 2)

    offset = None
    if left and right:
        lx, rx = left[0], right[0]
        cv2.line(result, (int(lx), h), (int(lx), 0), (255, 0, 255), 3)
        cv2.line(result, (int(rx), h), (int(rx), 0), (0, 165, 255), 3)
        cx = (lx + rx) / 2
        cv2.line(result, (int(cx), h), (int(cx), 0), (255, 255, 0), 3)
        offset = cx - img_center_x

    return offset

def detect_lines(edges_img, original_img):
    contours, _ = cv2.findContours(edges_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)
    rects = []
    h = original_img.shape[0]

    for cnt in contours:
        if cv2.contourArea(cnt) < MIN_AREA:
            continue

        rect = cv2.minAreaRect(cnt)
        (cx, cy), (rw, rh), angle = rect

        length = max(rw, rh)
        width  = min(rw, rh)

        if width < 1:
            continue

        aspect = length / width

        [vx, vy, x0, y0] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        angle_deg = float(abs(np.degrees(np.arctan2(vy, vx))) % 180)
        if angle_deg > 90:
            angle_deg = 180 - angle_deg

        if angle_deg > MAX_ANGLE_FROM_VERTICAL:
            continue

        if (width < MIN_TAPE_WIDTH or width > MAX_TAPE_WIDTH
                or aspect < MIN_ASPECT or length < MIN_LENGTH):
            continue

        print(f"  OK  | angle={angle_deg:.1f}° width={width:.1f} length={length:.1f} aspect={aspect:.1f}")

        rects.append(rect)

        # Fitovana linija kroz celu visinu slike
        if abs(vy) > 1e-6:
            t = (0 - y0) / vy
            x_top = int(x0 + t * vx)
            t = (h - y0) / vy
            x_bot = int(x0 + t * vx)
        else:
            x_top = x_bot = int(x0)

        cv2.line(result, (x_top, 0), (x_bot, h), (0, 255, 0), 2)

    w = original_img.shape[1]
    left_rects  = [r for r in rects if r[0][0] < w * 0.45]
    right_rects = [r for r in rects if r[0][0] > w * 0.55]

    left  = get_average_rect(left_rects)
    right = get_average_rect(right_rects)

    offset = draw_tape_contours(result, left, right, h)
    return result, offset

# --- GLAVNA PETLJA ---
for i in range(1, 154):
    filename = f"slika{i}.jpg"
    path = os.path.join(input_folder, filename)
    if not os.path.exists(path):
        continue

    img     = cv2.imread(path)
    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges  = cv2.Canny(blurred, 100, 150)
    kernel = np.ones((3, 3), np.uint8)
    edges  = cv2.dilate(edges, kernel, iterations=1)
    edges  = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    cv2.imwrite(os.path.join(canny_folder, f"canny{i}.jpg"), edges)

    res, offset = detect_lines(edges, blurred)
    cv2.imwrite(os.path.join(output_folder, f"slika{i}_final.jpg"), res)
    print(f"Obradjeno: {filename} | Offset: {offset}")