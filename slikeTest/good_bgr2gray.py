#!/usr/bin/env python3

import cv2
import numpy as np
import os

INPUT_DIR       = "Slike2"
OUTPUT_DIR      = "Slike2_tape"
TAPE_WIDTH      = 108
CANNY_LO        = 70
CANNY_HI        = 100
TARGET_WIDTH_PX = 2400

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- POMOCNE FUNKCIJE ---

def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    gornji_y = int(h * 0.3)
    pts = np.array([[(int(w * 0.15), gornji_y), (int(w * 0.85), gornji_y),
                     (w, h), (0, h)]], dtype=np.int32)
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)

def filter_lines(lines, angle_threshold=20):
    if lines is None:
        return None
    filtered = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = x2 - x1, y2 - y1
        angle = 90.0 if dx == 0 else abs(np.degrees(np.arctan2(dy, dx)))
        if angle > angle_threshold:
            filtered.append(line)
    return np.array(filtered) if filtered else None

def fit_line(points):
    if len(points) < 2:
        return None
    pts = np.array(points, dtype=np.float32)
    output = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    return float(output[0]), float(output[1]), float(output[2]), float(output[3])

def find_tape(lines, img_width):
    if lines is None:
        return None, None, None
    z_left  = img_width * 0.35
    z_right = img_width * 0.65
    left_p, center_p, right_p = [], [], []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cx = (x1 + x2) / 2.0
        if cx < z_left:
            left_p.extend([(x1, y1), (x2, y2)])
        elif cx < z_right:
            center_p.extend([(x1, y1), (x2, y2)])
        else:
            right_p.extend([(x1, y1), (x2, y2)])
    return fit_line(left_p), fit_line(right_p), fit_line(center_p)

def get_x_at_y(vx, vy, x0, y0, y):
    return int(x0 + ((y - y0) / vy) * vx) if vy != 0 else int(x0)

def get_angle_from_line(l):
    if l is None:
        return 0.0
    vx, vy, x0, y0 = l
    angle = np.degrees(np.arctan2(vx, -vy))
    if angle > 90:
        angle -= 180
    return angle

def get_intersection_angle(l_ang, r_ang):
    if (l_ang * r_ang) >= 0:
        return abs(abs(l_ang) - abs(r_ang))
    return abs(l_ang) + abs(r_ang)

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

# --- GLAVNA LOGIKA ---

def draw_tape(vis, left_line, right_line, center_line, img_center_x, h):
    h_img, w_img = vis.shape[:2]
    cmd    = 0.0
    offset = 0
    angle  = 0.0

    def steer_right(ll, rl):
        lx = get_x_at_y(*ll, h) if ll else None
        rx = get_x_at_y(*rl, h) if rl else None
        return calculate_steering_command(
            lx, rx, w_img,
            get_intersection_angle(get_angle_from_line(ll), get_angle_from_line(rl)),
            1
        )

    def steer_left(ll, rl):
        lx = get_x_at_y(*ll, h) if ll else None
        rx = get_x_at_y(*rl, h) if rl else None
        return calculate_steering_command(
            lx, rx, w_img,
            get_intersection_angle(get_angle_from_line(ll), get_angle_from_line(rl)),
            -1
        )

    def draw_line(l, color, thickness=3):
        pt1 = (get_x_at_y(*l, h),     h)
        pt2 = (get_x_at_y(*l, 0),     0)
        cv2.line(vis, pt1, pt2, color, thickness)

    # --- Odluka ---
    if left_line and right_line:
        l_ang        = get_angle_from_line(left_line)
        r_ang        = get_angle_from_line(right_line)
        intersect_ang = get_intersection_angle(l_ang, r_ang)

        lx = get_x_at_y(*left_line,  h)
        rx = get_x_at_y(*right_line, h)

        if l_ang > 0 and r_ang > 0:
            # Obe linije idu desno — skrecemo desno
            cmd = steer_right(left_line, right_line)

        elif l_ang < 0 and r_ang < 0:
            # Obe linije idu levo — skrecemo levo
            cmd = steer_left(left_line, right_line)

        elif l_ang < 0 and r_ang > 0:
            # V-oblik (obrnuto) — greska, obe su na istoj strani
            if lx > img_center_x and rx > img_center_x:
                cmd = steer_left(left_line, right_line)
            elif lx < img_center_x and rx < img_center_x:
                cmd = steer_right(left_line, right_line)
            else:
                cmd = 0.0

        elif l_ang > 0 and r_ang < 0:
            # Normalan presek (Lambda oblik) — staza ispred
            if intersect_ang > 110:
                cmd = 0.0
            elif lx > img_center_x / 3:
                cmd = steer_right(left_line, right_line)
            elif rx < img_center_x * 5 / 3:
                cmd = steer_left(left_line, right_line)
            else:
                cmd = 0.0

        draw_line(left_line,  (255, 165,   0))  # narandzasta
        draw_line(right_line, (128,   0, 128))  # ljubicasta
        cv2.putText(vis, f"L:{l_ang:+.1f} R:{r_ang:+.1f} Presek:{intersect_ang:.1f}",
                    (w_img - 320, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    elif left_line:
        l_ang = get_angle_from_line(left_line)
        cmd   = steer_right(left_line, None) if l_ang > -33.7 else steer_left(left_line, None)
        draw_line(left_line, (255, 165, 0))
        cv2.putText(vis, f"L:{l_ang:+.1f}", (w_img - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)

    elif right_line:
        r_ang = get_angle_from_line(right_line)
        cmd   = steer_left(None, right_line) if r_ang < 33.7 else steer_right(None, right_line)
        draw_line(right_line, (128, 0, 128))
        cv2.putText(vis, f"R:{r_ang:+.1f}", (w_img - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 0, 128), 2)

    # --- Centar staze i offset ---
    lx = get_x_at_y(*left_line,  h) if left_line  else None
    rx = get_x_at_y(*right_line, h) if right_line else None

    if lx is not None and rx is not None:
        center_x = (lx + rx) // 2
    elif lx is not None:
        center_x = int(lx + TARGET_WIDTH_PX / 2)
    elif rx is not None:
        center_x = int(rx - TARGET_WIDTH_PX / 2)
    else:
        center_x = img_center_x

    offset = center_x - img_center_x

    cv2.circle(vis, (center_x, h - 20), 10, (0, 0, 255), -1)
    cv2.line(vis, (img_center_x, h), (img_center_x, h - 80), (0, 0, 255), 2)
    cv2.putText(vis, f"Cmd:{cmd:+.2f}  Off:{offset:+d}px",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    return int(offset), float(angle), float(cmd)

# --- GLAVNA PETLJA ---

for i in range(1, 145):
    fpath = os.path.join(INPUT_DIR, f"slika{i}.jpg")
    if not os.path.exists(fpath):
        continue
    frame = cv2.imread(fpath)
    if frame is None:
        continue

    h, w = frame.shape[:2]
    gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred   = cv2.GaussianBlur(gray, (7, 7), 0)
    edges     = cv2.Canny(blurred, CANNY_LO, CANNY_HI)
    edges_roi = apply_trapezoid_roi(edges)

    lines_raw      = cv2.HoughLinesP(edges_roi, 1, np.pi/180, 25, minLineLength=15, maxLineGap=40)
    lines_filtered = filter_lines(lines_raw)

    vis = frame.copy()

    if lines_filtered is not None:
        for line in lines_filtered:
            x1, y1, x2, y2 = line[0]
            cv2.line(vis, (x1, y1), (x2, y2), (0, 255, 0), 1)

    left, right, center = find_tape(lines_filtered, w)
    offset, angle, cmd  = draw_tape(vis, left, right, center, w // 2, h)

    cv2.putText(vis, f"slika{i}", (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
    cv2.imwrite(os.path.join(OUTPUT_DIR, f"slika{i}.jpg"), vis)

print("Gotovo.")