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
        threshold=30,
        minLineLength=20,
        maxLineGap=40
    )
    lines = filter_lines(lines, angle_threshold=20)
    result = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)

    # Crtaj sve Hough segmente zeleno
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Fituj traku i crtaj plavu samo ako ima obe strane
    left_line, right_line = find_tape(lines, original_img.shape[1])
    offset = draw_tape(result, left_line, right_line, original_img.shape[0])
    return result, offset, left_line, right_line

def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    
    pts = np.array([[
        (int(w * 0.15), 0),       # gornji levi
        (int(w * 0.85), 0),       # gornji desni
        (w,            h),       # donji desni
        (0,            h)        # donji levi
    ]], dtype=np.int32)
    
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

def filter_lines(lines,angle_threshold=20):
    if lines is None:
        return None
    filtered=[]
    for line in lines:
        x1,y1,x2,y2=line[0]
        dx=x2-x1
        dy=y2-y1
        if dx==0:
            angle=90.0
        else:
            angle=abs(np.degrees(np.arctan2(dy,dx)))
        if(angle>angle_threshold):
            filtered.append(line)
    return np.array(filtered) if filtered else None

def find_tape(lines, img_width):
    if lines is None:
        return None, None

    mid = img_width // 2
    left_points, right_points = [], []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0:
            continue
        slope = dy / dx
        cx = (x1 + x2) // 2

        if slope < 0 and cx < mid:
            left_points.extend([(x1, y1), (x2, y2)])   # leva ivica, leva strana
        elif slope > 0 and cx > mid:
            right_points.extend([(x1, y1), (x2, y2)])  # desna ivica, desna strana
        elif slope < 0 and cx > mid:
            right_points.extend([(x1, y1), (x2, y2)])  # leva ivica vidljiva desno → nagazili levu
        elif slope > 0 and cx < mid:
            left_points.extend([(x1, y1), (x2, y2)])   # desna ivica vidljiva levo → nagazili desnu

    left_line = fit_line(left_points)
    right_line = fit_line(right_points)
    return left_line, right_line

def fit_line(points):
    if len(points) < 2:
        return None
    pts = np.array(points, dtype=np.float32)
    output = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    return float(output[0]), float(output[1]), float(output[2]), float(output[3])

def get_x_at_y(vx,vy,x0,y0,y):
    if vy==0:
        return int(x0)
    t=(y-y0)/vy
    return int(x0+t*vx)

def draw_tape(result, left_line, right_line, img_height):
    h = img_height
    img_center = result.shape[1] // 2

    if left_line is not None and right_line is not None:
        vx_l, vy_l, x0_l, y0_l = left_line
        vx_r, vy_r, x0_r, y0_r = right_line

        lx_bot = get_x_at_y(vx_l, vy_l, x0_l, y0_l, h)
        lx_top = get_x_at_y(vx_l, vy_l, x0_l, y0_l, 0)
        rx_bot = get_x_at_y(vx_r, vy_r, x0_r, y0_r, h)
        rx_top = get_x_at_y(vx_r, vy_r, x0_r, y0_r, 0)

        cx_bot = (lx_bot + rx_bot) // 2
        cx_top = (lx_top + rx_top) // 2
        cv2.line(result, (cx_bot, h-1), (cx_top, 0), (255, 0, 0), 2)

        offset = cx_bot - img_center
        cv2.putText(result, f"offset: {offset:+d}px", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return offset

    elif left_line is not None:
        vx, vy, x0, y0 = left_line
        cx_bot = get_x_at_y(vx, vy, x0, y0, h)
        cx_top = get_x_at_y(vx, vy, x0, y0, 0)
        TAPE_WIDTH = 100
        cv2.line(result, (cx_bot + TAPE_WIDTH//2, h-1), (cx_top + TAPE_WIDTH//2, 0), (255, 0, 0), 2)
        offset = (cx_bot + TAPE_WIDTH//2) - img_center
        cv2.putText(result, f"offset(L): {offset:+d}px", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        return offset

    elif right_line is not None:
        vx, vy, x0, y0 = right_line
        cx_bot = get_x_at_y(vx, vy, x0, y0, h)
        cx_top = get_x_at_y(vx, vy, x0, y0, 0)
        TAPE_WIDTH = 100
        cv2.line(result, (cx_bot - TAPE_WIDTH//2, h-1), (cx_top - TAPE_WIDTH//2, 0), (255, 0, 0), 2)
        offset = (cx_bot - TAPE_WIDTH//2) - img_center
        cv2.putText(result, f"offset(R): {offset:+d}px", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        return offset

    return None
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

    edges = cv2.Canny(blurred, 100, 150)
    edges = apply_trapezoid_roi(edges)
    kernel = np.ones((3, 3), np.uint8)
    edges_cleared = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    cv2.imwrite(os.path.join(canny_folder, f"canny{i}.jpg"), edges_cleared)

    final_result,offset,left_line,right_line = detect_lines(edges_cleared, blurred)
    cv2.imwrite(os.path.join(output_folder, f"slika{i}_final.jpg"), final_result)

    if offset is not None:
        if left_line is not None and right_line is not None:
            status = "TRAKA OK"
        elif left_line is not None:
            status = "SAMO LEVA → skreni desno"
        else:
            status = "SAMO DESNA → skreni levo"
        print(f"  → offset: {offset:+d}px | {status}")
    else:
        print(f"  → traka nije detektovana")
    print(f"  → {time.time() - t0:.3f}s")

print(f"\nGotovo!\nRezultati su u: {output_folder}\nOčišćeni Canny u: {canny_folder}\nHeatmape u: {heatmap_folder}")