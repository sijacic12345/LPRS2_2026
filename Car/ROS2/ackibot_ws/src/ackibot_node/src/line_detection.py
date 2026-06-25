import cv2
import numpy as np

TAPE_WIDTH = 108

def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    pts = np.array([[(int(w * 0.15), 0), (int(w * 0.85), 0), (w, h), (0, h)]], dtype=np.int32)
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

def detect_lines_logic(frame):
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    edges = cv2.Canny(blurred, 100, 150)
    edges_roi = apply_trapezoid_roi(edges)
    
    lines = cv2.HoughLinesP(edges_roi, 1, np.pi/180, 30, minLineLength=20, maxLineGap=40)
    
    result = frame.copy()
    offset = 0 # Default: vozi pravo
    
    if lines is not None:
        # Pronađi sredinu svih detektovanih linija (pojednostavljeno)
        # Ovde možeš dodati poziv za tvoju find_tape() funkciju
        x_coords = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            x_coords.append((x1 + x2) / 2)
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Izračunaj srednju X koordinatu detektovanih linija
        avg_line_x = np.mean(x_coords)
        img_center_x = w / 2
        
        # Offset je udaljenost od centra
        offset = avg_line_x - img_center_x
        
        # Vizuelno obeleži centar i offset
        cv2.line(result, (int(avg_line_x), h), (int(avg_line_x), 0), (255, 0, 0), 2)
        cv2.line(result, (int(img_center_x), h), (int(img_center_x), 0), (0, 0, 255), 2)
        
    return result, int(offset)