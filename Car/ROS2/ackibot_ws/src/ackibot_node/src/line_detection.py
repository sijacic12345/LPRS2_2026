import cv2
import numpy as np
import time
from itertools import combinations

# --- KONSTANTE ---
TAPE_WIDTH      = 33       # px na robotu (640px wide) — ne menjati za LP batch
TAPE_TOL        = 10
ANGLE_TOL       = 15
MIN_ANGLE       = 10
TARGET_WIDTH_PX = 735     # ocekivana sirina trake u px za calculate_steering_command
CANNY_LO        = 70
CANNY_HI        = 100

# --- ROI ---
def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    gornji_y = int(h * 0.3)
    pts = np.array([[(int(w * 0.15), gornji_y), (int(w * 0.85), gornji_y),
                     (w, h), (0, h)]], dtype=np.int32)
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

# --- HOUGH FILTER ---
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

# --- GEOMETRIJA ---
def line_angle_raw(x1, y1, x2, y2):
    """Ugao [0, 180) od horizontale."""
    return np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180

def get_angle_from_seg(seg):
    """Ugao segmenta od vertikale [-90, 90]."""
    if seg is None:
        return 0.0
    x1, y1, x2, y2 = seg
    vx = x2 - x1
    vy = y2 - y1
    angle = np.degrees(np.arctan2(vx, -vy))
    if angle > 90:
        angle -= 180
    return angle

def get_intersection_angle(l_ang, r_ang):
    if (l_ang * r_ang) >= 0:
        return abs(abs(l_ang) - abs(r_ang))
    return abs(l_ang) + abs(r_ang)

def point_to_line_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length = np.sqrt(dx*dx + dy*dy)
    if length == 0:
        return np.sqrt((px - x1)**2 + (py - y1)**2)
    return abs(dy*px - dx*py + x2*y1 - y2*x1) / length

def x_at_y(x1, y1, x2, y2, target_y):
    if y1 == y2:
        return (x1 + x2) / 2
    t = (target_y - y1) / (y2 - y1)
    return x1 + t * (x2 - x1)

# --- DETEKCIJA PARA ---
def find_best_tape_pair(lines):
    if lines is None or len(lines) < 2:
        return None
    best       = None
    best_score = float('inf')
    for la, lb in combinations(lines, 2):
        angle_a = line_angle_raw(*la)
        angle_b = line_angle_raw(*lb)
        angle_diff = abs(angle_a - angle_b)
        if angle_diff > 90:
            angle_diff = 180 - angle_diff
        if angle_diff > ANGLE_TOL:
            continue
        mx_b = (la[0] + la[2]) / 2
        my_b = (la[1] + la[3]) / 2
        dist     = point_to_line_dist(mx_b, my_b, *lb)
        dist_err = abs(dist - TAPE_WIDTH)
        if dist_err > TAPE_TOL:
            continue
        score = angle_diff + dist_err * 0.5
        if score < best_score:
            best_score = score
            best = (la, lb)
    return best

# --- UPRAVLJANJE ---
def calculate_steering_command(lx, rx, img_width, angle, sign):
    if lx is not None and rx is not None:
        center_staze = (lx + rx) / 2
    elif lx is not None:
        center_staze = lx + TARGET_WIDTH_PX / 2
    elif rx is not None:
        center_staze = rx - TARGET_WIDTH_PX / 2
    else:
        center_staze = img_width / 2

    error = (center_staze - img_width / 2.0) / (img_width / 2.0)

    effective_angle = 0.0
    if abs(angle) > 20.0:
        effective_angle = (angle - 20.0) if angle > 0 else (angle + 20.0)

    Kp = 0.5
    Kd = 0.05
    steering = error * Kp + effective_angle * Kd
    final = float(np.clip(steering, -0.4, 0.4))

    if final > 0 and sign == -1:
        final = -final
    elif final < 0 and sign == 1:
        final = abs(final)

    return final

def get_cmd(left_seg, right_seg, img_width, h):
    """Računa steering komandu na osnovu para segmenata."""
    lx = int(x_at_y(*left_seg,  h)) if left_seg  else None
    rx = int(x_at_y(*right_seg, h)) if right_seg else None

    l_ang = get_angle_from_seg(left_seg)
    r_ang = get_angle_from_seg(right_seg)
    intersect_ang = get_intersection_angle(l_ang, r_ang)

    if left_seg and right_seg:
        if l_ang > 0 and r_ang > 0:
            return calculate_steering_command(lx, rx, img_width, intersect_ang,  1)
        elif l_ang < 0 and r_ang < 0:
            return calculate_steering_command(lx, rx, img_width, intersect_ang, -1)
        elif l_ang < 0 and r_ang > 0:
            # V-oblik — greska
            img_cx = img_width // 2
            if lx > img_cx and rx > img_cx:
                return calculate_steering_command(lx, rx, img_width, intersect_ang, -1)
            elif lx < img_cx and rx < img_cx:
                return calculate_steering_command(lx, rx, img_width, intersect_ang,  1)
            return 0.0
        else:
            # Lambda oblik — normalna staza ispred
            if intersect_ang > 110:
                return 0.0
            img_cx = img_width // 2
            if lx > img_cx / 3:
                return calculate_steering_command(lx, rx, img_width, intersect_ang,  1)
            elif rx < img_cx * 5 / 3:
                return calculate_steering_command(lx, rx, img_width, intersect_ang, -1)
            return 0.0

    elif left_seg:
        return calculate_steering_command(lx, None, img_width, intersect_ang,
                                          1 if l_ang > -33.7 else -1)
    elif right_seg:
        return calculate_steering_command(None, rx, img_width, intersect_ang,
                                          -1 if r_ang < 33.7 else 1)
    return 0.0

# --- GLAVNA FUNKCIJA ---
def detect_lines_logic(frame):
    t_start = time.perf_counter()

    h, w = frame.shape[:2]
    img_center_x = w // 2
    y_eval = h - 1

    gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred   = cv2.GaussianBlur(gray, (7, 7), 0)
    edges     = cv2.Canny(blurred, CANNY_LO, CANNY_HI)
    edges_roi = apply_trapezoid_roi(edges)

    lines_raw      = cv2.HoughLinesP(edges_roi, 1, np.pi/180, 30, minLineLength=20, maxLineGap=40)
    lines_filtered = filter_horizontal(lines_raw)

    result = frame.copy()
    offset = 0
    cmd    = 0.0

    # Zelene Hough linije uvek
    if lines_filtered:
        for x1, y1, x2, y2 in lines_filtered:
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 1)

    pair = find_best_tape_pair(lines_filtered)

    if pair:
        la, lb = pair
        if (la[0] + la[2]) < (lb[0] + lb[2]):
            left_seg, right_seg = la, lb
        else:
            left_seg, right_seg = lb, la

        lx = int(x_at_y(*left_seg,  y_eval))
        rx = int(x_at_y(*right_seg, y_eval))
        cx = (lx + rx) // 2
        offset = cx - img_center_x
        cmd    = get_cmd(left_seg, right_seg, w, h)

        cv2.line(result, (left_seg[0],  left_seg[1]),  (left_seg[2],  left_seg[3]),  (0, 128, 255), 3)
        cv2.line(result, (right_seg[0], right_seg[1]), (right_seg[2], right_seg[3]), (255, 0, 255), 3)
        cv2.line(result, (cx, h), (cx, h // 2), (255, 0, 0), 3)

        l_ang = get_angle_from_seg(left_seg)
        r_ang = get_angle_from_seg(right_seg)
        cv2.putText(result, f"L:{l_ang:+.1f} R:{r_ang:+.1f} Cmd:{cmd:+.2f}",
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

    # Centar kamere
    cv2.line(result, (img_center_x, h), (img_center_x, h - 60), (0, 0, 255), 2)
    cv2.putText(result, f"offset={offset:+d}px",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

    t_end = time.perf_counter()
    print(f"Obrada frejma: {(t_end - t_start)*1000:.2f}ms  offset={offset:+d}px  cmd={cmd:+.2f}")

    return result, int(offset), float(cmd)