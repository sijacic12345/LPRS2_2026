import cv2
import numpy as np
import os
import time


"""
POKRETANJE OKRUZENJA:
source ~/cv_env/bin/activate
python3 line_detectionV2.py
"""

# --- PODEŠAVANJA ---
input_folder  = 'Slike2'
output_folder = 'final'
canny_folder  = 'canny_cleared'
heatmap_folder = 'heatmap'
TAPE_WIDTH = 64  # širina trake u pikselima

# Kreiranje foldera ako ne postoje
for folder in [output_folder, canny_folder, heatmap_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- FUNKCIJE ---

def filter_lines(lines, angle_threshold=20, horizontal_threshold=20):
    if lines is None: return None
    filtered = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = x2 - x1, y2 - y1
        # Ugao u odnosu na horizontalu (0 stepeni)
        angle = abs(np.degrees(np.arctan2(-dy, dx)))
        
        # Odbaci ako je linija previše "ravna" (horizontalna)
        if angle < horizontal_threshold:
            continue
            
        # Odbaci ako je previše blizu vertikale (opciono, ako traka nije vertikalna)
        # Odbaci ako je ugao previše oštar (buka)
        if angle > angle_threshold:
            filtered.append(line)
            
    return np.array(filtered) if filtered else None

def fit_line(points):
    if len(points) < 2: return None
    pts = np.array(points, dtype=np.float32)
    output = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    return float(output[0]), float(output[1]), float(output[2]), float(output[3])

def get_x_at_y(vx, vy, x0, y0, y):
    if vy == 0: return int(x0)
    t = (y - y0) / vy
    return int(x0 + t * vx)

def find_tape(lines, img_width):
    if lines is None: return None, None, None
    z_left, z_right = img_width * 0.35, img_width * 0.65
    left_pts, center_pts, right_pts = [], [], []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cx = (x1 + x2) / 2.0
        if cx < z_left: left_pts.extend([(x1, y1), (x2, y2)])
        elif cx < z_right: center_pts.extend([(x1, y1), (x2, y2)])
        else: right_pts.extend([(x1, y1), (x2, y2)])
    return fit_line(left_pts), fit_line(right_pts), fit_line(center_pts)

def lines_are_valid(left, right, max_angle_diff=50, max_conv=30):
    if left is None or right is None: return True
    angle_l = np.degrees(np.arctan2(left[0], left[1]))
    angle_r = np.degrees(np.arctan2(right[0], right[1]))
    if abs(angle_l - angle_r) > max_angle_diff: return False
    if angle_l > max_conv and angle_r < -max_conv: return False
    return True

def draw_tape(result, left, right, center, h):
    w = result.shape[1]
    img_center_x = w // 2

    # 1. Referentna crvena linija
    cv2.line(result, (img_center_x, h - 1), (img_center_x, 0), (0, 0, 255), 2)

    # 2. Žute isprekidane granice
    for frac in [0.35, 0.65]:
        xz = int(w * frac)
        for y in range(0, h, 20):
            cv2.line(result, (xz, y), (xz, y + 10), (0, 200, 255), 2)

    def get_angle_horiz(vx, vy):
        return np.degrees(np.arctan2(-vy, vx))

    offset = None
    
    if left and right:
        lx_b, lx_t = get_x_at_y(*left, h), get_x_at_y(*left, 0)
        rx_b, rx_t = get_x_at_y(*right, h), get_x_at_y(*right, 0)
        
        # Leva ljubičasta, desna narandžasta
        cv2.line(result, (lx_b, h), (lx_t, 0), (255, 0, 255), 3) 
        cv2.line(result, (rx_b, h), (rx_t, 0), (0, 165, 255), 3)
        
        # Plava putanja
        cx_b, cx_t = (lx_b + rx_b) // 2, (lx_t + rx_t) // 2
        cv2.line(result, (cx_b, h), (cx_t, 0), (255, 255, 0), 3)
        
        # Ugao i tvoja logika validacije
        ang_l = get_angle_horiz(left[0], left[1])
        ang_r = get_angle_horiz(right[0], right[1])
        
        if (ang_l * ang_r) > 0:
            presek_ugao = abs(ang_l) + abs(ang_r)
        else:
            presek_ugao = 180 - (abs(ang_l) + abs(ang_r))
            
        is_invalid = ((ang_l * ang_r) < 0 and presek_ugao > 90)
        
        # Ispis u uglu
        status = "NE" if is_invalid else "DA"
        cv2.putText(result, f"Presek: {presek_ugao:.1f} | Valid: {status}", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        offset = cx_b - img_center_x

    elif center:
        cx_b, cx_t = get_x_at_y(*center, h), get_x_at_y(*center, 0)
        cv2.line(result, (cx_b, h), (cx_t, 0), (255, 255, 0), 3)
        cv2.putText(result, f"Centar Ugao: {get_angle_horiz(center[0], center[1]):.1f}", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        offset = cx_b - img_center_x

    return offset

def detect_lines(edges_img, original_img):
    lines = cv2.HoughLinesP(
        edges_img, rho=1, theta=np.pi/180, 
        threshold=50, minLineLength=60, maxLineGap=70
    )
    
    result = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)
    
    if lines is not None:
        # PRVO FILTRIRAMO, PA ONDA CRTAMO
        filtered = filter_lines(lines, angle_threshold=20, horizontal_threshold=10)
        
        if filtered is not None:
            for line in filtered:
                x1, y1, x2, y2 = line[0]
                cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            left, right, center = find_tape(filtered, original_img.shape[1])
        else:
            left, right, center = None, None, None
    else:
        left, right, center = None, None, None

    offset = draw_tape(result, left, right, center, original_img.shape[0])
    return result, offset

# --- GLAVNA PETLJA ---
for i in range(1, 157):
    filename = f"slika{i}.jpg"
    path = os.path.join(input_folder, filename)
    if not os.path.exists(path): continue

    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Heatmap
    sobelx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    mag = cv2.normalize(cv2.magnitude(sobelx, sobely), None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
    cv2.imwrite(os.path.join(heatmap_folder, f"heatmap{i}.jpg"), cv2.applyColorMap(mag, cv2.COLORMAP_JET))

    # Canny
    edges=cv2.Canny(blurred, 100, 150)
    kernel=np.ones((3,3),np.uint8)
    edges=cv2.dilate(edges,kernel,iterations=1)
    edges=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,kernel)
    #edges = cv2.morphologyEx(cv2.Canny(blurred, 100, 150), cv2.MORPH_CLOSE, np.ones((3,3)))
    cv2.imwrite(os.path.join(canny_folder, f"canny{i}.jpg"), edges)

    # Detekcija
    res, offset = detect_lines(edges, blurred)
    cv2.imwrite(os.path.join(output_folder, f"slika{i}_final.jpg"), res)
    print(f"Obradjeno: {filename} | Offset: {offset}")