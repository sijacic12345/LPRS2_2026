import cv2
import numpy as np
import os
import time

#source ~/cv_env/bin/activate
#python3 line_detection.py

input_folder = 'slike'
output_folder = 'final'
canny_folder = 'canny_cleared'
heatmap_folder = 'heatmap'

for folder in [output_folder, canny_folder, heatmap_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

start = time.time()

def detect_lines(edges_img, original_img):
    lines = cv2.HoughLinesP(
        edges_img,
        rho=1,
        theta=np.pi / 180,
        threshold=10,
        minLineLength=10,
        maxLineGap=40
    )
    result = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
    return result

def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    
    pts = np.array([[
        (int(w * 0.2), 0),       # gornji levi
        (int(w * 0.8), 0),       # gornji desni
        (w,            h),       # donji desni
        (0,            h)        # donji levi
    ]], dtype=np.int32)
    
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

for i in range(39):
    t0 = time.time()
    filename = f"slika{i}.jpg"
    input_path = os.path.join(input_folder, filename)
    if not os.path.exists(input_path):
        continue

    img = cv2.imread(input_path)
    if img is None:
        continue

    print(f"Obrađujem: {filename}...")

    h, w = img.shape[:2]
    cropped = img[h//2:h, 0:w]

    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    #gray = cv2.equalizeHist(gray)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Heatmap gradijenta
    sobelx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(sobelx, sobely)
    mag_norm = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
    heatmap = cv2.applyColorMap(mag_norm, cv2.COLORMAP_JET)
    cv2.imwrite(os.path.join(heatmap_folder, f"heatmap{i}.jpg"), heatmap)

    edges = cv2.Canny(blurred, 0, 50)
    #edges = apply_trapezoid_roi(edges)
    kernel = np.ones((3, 3), np.uint8)
    edges_cleared = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    cv2.imwrite(os.path.join(canny_folder, f"canny{i}.jpg"), edges_cleared)

    final_result = detect_lines(edges_cleared, blurred)
    cv2.imwrite(os.path.join(output_folder, f"slika{i}_final.jpg"), final_result)
    print(f"  → {time.time() - t0:.3f}s")

print(f"\nGotovo!\nRezultati su u: {output_folder}\nOčišćeni Canny u: {canny_folder}\nHeatmape u: {heatmap_folder}")