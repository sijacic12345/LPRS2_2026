import cv2
import numpy as np
import time

TAPE_WIDTH = 108

def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    pts = np.array([[(int(w * 0.15), 0), (int(w * 0.85), 0), (w, h), (0, h)]], dtype=np.int32)
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

def fit_line(points):
    """Prilagođava pravu skupu tačaka koristeći najmanje kvadrate."""
    if len(points) < 2:
        return None
    pts = np.array(points, dtype=np.float32)
    # output = [vx, vy, x0, y0]
    output = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    return float(output[0]), float(output[1]), float(output[2]), float(output[3])

def find_tape(lines, img_width):
    """Razvrstava linije u tri zone i pravi model ivica trake."""
    if lines is None:
        return None, None, None

    z_left = img_width * 0.35
    z_right = img_width * 0.65

    left_points, right_points, center_points = [], [], []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        cx = (x1 + x2) / 2.0
        
        # Razvrstavanje linija po poziciji (Leva, Srednja, Desna)
        if cx < z_left:
            left_points.extend([(x1, y1), (x2, y2)])
        elif cx < z_right:
            center_points.extend([(x1, y1), (x2, y2)])
        else:
            right_points.extend([(x1, y1), (x2, y2)])

    return fit_line(left_points), fit_line(right_points), fit_line(center_points)

def get_x_at_y(vx, vy, x0, y0, y):
    """Računa X koordinatu tačke na pravoj za zadati Y nivo."""
    if vy == 0: return int(x0)
    t = (y - y0) / vy
    return int(x0 + t * vx)

def detect_lines_logic(frame):
    t_start=time.perf_counter()
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 100, 150)
    edges_roi = apply_trapezoid_roi(edges)
    
    lines = cv2.HoughLinesP(edges_roi, 1, np.pi/180, 30, minLineLength=20, maxLineGap=40)
    
    result = frame.copy()
    offset = 0 
    
    # Koristimo tvoju find_tape logiku
    # Napomena: Očekujemo da su fit_line i ostale pomoćne funkcije tu
    left_line, right_line, center_line = find_tape(lines, w)
    
    # Vizuelizacija i računanje offset-a
    img_center_x = w // 2
    
    if left_line and right_line:
        # Slučaj: Imamo obe ivice - sredina je između njih
        lx_bot = get_x_at_y(*left_line, h)
        rx_bot = get_x_at_y(*right_line, h)
        cx_bot = (lx_bot + rx_bot) // 2
        offset = cx_bot - img_center_x
        cv2.line(result, (lx_bot, h), (rx_bot, h), (0, 255, 0), 5) # Zelena traka
    elif center_line:
        # Slučaj: Imamo samo centralnu liniju
        cx_bot = get_x_at_y(*center_line, h)
        offset = cx_bot - img_center_x
        cv2.line(result, (cx_bot, h), (cx_bot, 0), (255, 255, 0), 2)
    elif left_line:
        # Slučaj: Samo leva ivica
        lx_bot = get_x_at_y(*left_line, h)
        offset = (lx_bot + TAPE_WIDTH // 2) - img_center_x
    elif right_line:
        # Slučaj: Samo desna ivica
        rx_bot = get_x_at_y(*right_line, h)
        offset = (rx_bot - TAPE_WIDTH // 2) - img_center_x

    # Crtanje centra kamere za referencu
    cv2.line(result, (img_center_x, h), (img_center_x, h-50), (0, 0, 255), 3)

    #TIMER
    t_end=time.perf_counter()
    duration=(t_end-t_start)*1000

    print(f"Obrada frejma: {duration:.2f}ms")
    
    return result, int(offset)