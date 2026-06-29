import cv2
import numpy as np
import time
from itertools import combinations

TAPE_WIDTH = 108
TAPE_TOL   = 40
ANGLE_TOL  = 15
MIN_ANGLE  = 10

def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    pts = np.array([[(int(w * 0.15), 0), (int(w * 0.85), 0), (w, h), (0, h)]], dtype=np.int32)
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

def filter_horizontal(lines, min_angle_deg=MIN_ANGLE):
    if lines is None:
        return None
    filtered = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(abs(y2 - y1), abs(x2 - x1))))
        if angle >= min_angle_deg:
            filtered.append((x1, y1, x2, y2))
    return filtered if filtered else None

def line_angle(x1, y1, x2, y2):
    return np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180

def point_to_line_dist(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx*dx + dy*dy)
    if length == 0:
        return np.sqrt((px-x1)**2 + (py-y1)**2)
    return abs(dy*px - dx*py + x2*y1 - y2*x1) / length

def x_at_y(x1, y1, x2, y2, target_y):
    if y1 == y2:
        return (x1 + x2) / 2
    t = (target_y - y1) / (y2 - y1)
    return x1 + t * (x2 - x1)

def find_best_tape_pair(lines):
    if lines is None or len(lines) < 2:
        return None
    best = None
    best_score = float('inf')
    for la, lb in combinations(lines, 2):
        angle_a = line_angle(*la)
        angle_b = line_angle(*lb)
        angle_diff = abs(angle_a - angle_b)
        if angle_diff > 90:
            angle_diff = 180 - angle_diff
        if angle_diff > ANGLE_TOL:
            continue
        mx_b = (la[0] + la[2]) / 2
        my_b = (la[1] + la[3]) / 2
        dist = point_to_line_dist(mx_b, my_b, *lb)
        dist_err = abs(dist - TAPE_WIDTH)
        if dist_err > TAPE_TOL:
            continue
        score = angle_diff + dist_err * 0.5
        if score < best_score:
            best_score = score
            best = (la, lb)
    return best

def detect_lines_logic(frame):
    t_start = time.perf_counter()

    h, w = frame.shape[:2]
    img_center_x = w // 2
    y_eval = h - 1

    gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred   = cv2.GaussianBlur(gray, (7, 7), 0)
    edges     = cv2.Canny(blurred, 70, 100)
    edges_roi = apply_trapezoid_roi(edges)

    lines_raw      = cv2.HoughLinesP(edges_roi, 1, np.pi/180, 30, minLineLength=20, maxLineGap=40)
    lines_filtered = filter_horizontal(lines_raw)

    result = frame.copy()
    offset = 0

    pair = find_best_tape_pair(lines_filtered)

    if pair:
        la, lb = pair
        # Leva/desna po X poziciji
        if (la[0] + la[2]) < (lb[0] + lb[2]):
            left_seg, right_seg = la, lb
        else:
            left_seg, right_seg = lb, la

        lx = int(x_at_y(*left_seg,  y_eval))
        rx = int(x_at_y(*right_seg, y_eval))
        cx = (lx + rx) // 2
        offset = cx - img_center_x

        cv2.line(result, (left_seg[0],  left_seg[1]),  (left_seg[2],  left_seg[3]),  (0, 128, 255), 3)  # narandzasta
        cv2.line(result, (right_seg[0], right_seg[1]), (right_seg[2], right_seg[3]), (255, 0, 255), 3)  # ljubicasta
        cv2.line(result, (cx, h), (cx, h // 2), (255, 0, 0), 3)                                         # plava odluka

    # Centar kamere
    cv2.line(result, (img_center_x, h), (img_center_x, h - 60), (0, 0, 255), 2)

    t_end = time.perf_counter()
    print(f"Obrada frejma: {(t_end - t_start)*1000:.2f}ms  offset={offset:+d}px")

    return result, int(offset)