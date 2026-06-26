import cv2
import numpy as np
import os
import time

"""
POKRETANJE OKRUZENJA:
source ~/cv_env/bin/activate
python3 line_detection.py
"""

input_folder  = 'Slike2'
output_folder = 'final'
canny_folder  = 'canny_cleared'
heatmap_folder = 'heatmap'

TAPE_WIDTH = 108  # širina trake u pikselima

for folder in [output_folder, canny_folder, heatmap_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

start = time.time()


def apply_trapezoid_roi(edges_img):
    h, w = edges_img.shape[:2]
    pts = np.array([[
        (int(w * 0.15), 0),
        (int(w * 0.85), 0),
        (w,             h),
        (0,             h)
    ]], dtype=np.int32)
    mask = np.zeros_like(edges_img)
    cv2.fillPoly(mask, pts, 255)
    return cv2.bitwise_and(edges_img, mask)


def filter_lines(lines, angle_threshold=20):
    if lines is None:
        return None
    filtered = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        angle = 90.0 if dx == 0 else abs(np.degrees(np.arctan2(dy, dx)))
        if angle > angle_threshold:
            filtered.append(line)
    return np.array(filtered) if filtered else None


def find_tape(lines, img_width):
    """
    3 zone:
      Leva:    x in [0,      w*0.35)
      Srednja: x in [w*0.35, w*0.65)
      Desna:   x in [w*0.65, w)
    """
    if lines is None:
        return None, None, None

    z_left  = img_width * 0.35
    z_right = img_width * 0.65

    left_points   = []
    center_points = []
    right_points  = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        cx = (x1 + x2) / 2.0

        if cx < z_left:
            left_points.extend([(x1, y1), (x2, y2)])
        elif cx < z_right:
            center_points.extend([(x1, y1), (x2, y2)])
        else:
            right_points.extend([(x1, y1), (x2, y2)])

    return fit_line(left_points), fit_line(right_points), fit_line(center_points)


def fit_line(points):
    if len(points) < 2:
        return None
    pts = np.array(points, dtype=np.float32)
    output = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    return float(output[0]), float(output[1]), float(output[2]), float(output[3])


def get_x_at_y(vx, vy, x0, y0, y):
    if vy == 0:
        return int(x0)
    t = (y - y0) / vy
    return int(x0 + t * vx)


def lines_are_valid(left_line, right_line, max_angle_diff=50, max_convergence_deg=30):
    """
    Proverava da li su leva i desna linija validne ivice trake:

    1. Ugaona razlika — ivice trake moraju biti približno paralelne.
       Ako je razlika u nagibu > max_angle_diff stepeni → lažna detekcija.

    2. Konvergencija — linije ne smeju formirati V oblik (spajati se unutar slike).
       Ako obe linije naginje ka centru previše → V oblik → odbacujemo.
    """
    if left_line is None or right_line is None:
        return True

    def line_angle_deg(line):
        vx, vy, x0, y0 = line
        if vy == 0:
            return 90.0
        return np.degrees(np.arctan2(vx, vy))

    angle_left  = line_angle_deg(left_line)
    angle_right = line_angle_deg(right_line)

    # Provera 1: paralelnost
    angle_diff = abs(angle_left - angle_right)
    if angle_diff > max_angle_diff:
        print(f"  ⚠ Odbačene linije — prevelika razlika nagiba: {angle_diff:.1f} deg "
              f"(leva={angle_left:.1f}, desna={angle_right:.1f})")
        return False

    # Provera 2: V oblik
    if angle_left > max_convergence_deg and angle_right < -max_convergence_deg:
        print(f"  ⚠ Odbačene linije — V oblik detektovan "
              f"(leva={angle_left:.1f}, desna={angle_right:.1f})")
        return False

    return True


def draw_tape(result, left_line, right_line, center_line, img_height, valid=True):
    h  = img_height
    w  = result.shape[1]
    img_center_x = w // 2

    # Crvena referentna linija
    cv2.line(result, (img_center_x, h - 1), (img_center_x, 0), (0, 0, 255), 2)

    # Žute isprekidane granice zona (35% i 65%)
    for frac in [0.35, 0.65]:
        xz = int(w * frac)
        y, draw = 0, True
        while y < h:
            y_end = min(y + (12 if draw else 8), h)
            if draw:
                cv2.line(result, (xz, y), (xz, y_end), (0, 200, 255), 2)
            y, draw = y_end, not draw

    def calculate_angle(cx_bot, cx_top, h):
        v_blue = np.array([cx_top - cx_bot, -h])
        v_red  = np.array([0, -h])
        dot = np.dot(v_blue, v_red)
        det = v_blue[0] * v_red[1] - v_blue[1] * v_red[0]
        return np.degrees(np.arctan2(det, dot))

    def angle_of_line(line):
        vx, vy, x0, y0 = line
        cx_bot = get_x_at_y(vx, vy, x0, y0, h)
        cx_top = get_x_at_y(vx, vy, x0, y0, 0)
        return calculate_angle(cx_bot, cx_top, h)

    def draw_valid_badge():
        status_text  = "VALID"    if valid else "INVALID"
        status_color = (0, 220, 0) if valid else (0, 0, 220)
        (text_w, text_h), _ = cv2.getTextSize(
            status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        text_x = w - text_w - 12
        text_y = text_h + 12
        cv2.rectangle(result,
                      (text_x - 6,          text_y - text_h - 6),
                      (text_x + text_w + 6, text_y + 6),
                      (30, 30, 30), -1)
        cv2.putText(result, status_text,
                    (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    def draw_info(cx_bot, cx_top, label, angle_left=None, angle_right=None, angle_center=None):
        cv2.line(result, (cx_bot, h - 1), (cx_top, 0), (255, 0, 0), 2)
        offset = cx_bot - img_center_x
        y_pos = 30
        cv2.putText(result, f"{label} | Offset: {offset:+d}px",
                    (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        y_pos += 28
        if angle_center is not None:
            cv2.putText(result, f"Ugao trake:  {angle_center:+.1f} deg",
                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            y_pos += 24
        if angle_left is not None:
            cv2.putText(result, f"Ugao leve:   {angle_left:+.1f} deg",
                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 100), 2)
            y_pos += 22
        if angle_right is not None:
            cv2.putText(result, f"Ugao desne:  {angle_right:+.1f} deg",
                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 200, 255), 2)
        draw_valid_badge()
        return offset

    # Slučaj 1: Obe ivice
    if left_line is not None and right_line is not None:
        lx_bot = get_x_at_y(*left_line,  h)
        lx_top = get_x_at_y(*left_line,  0)
        rx_bot = get_x_at_y(*right_line, h)
        rx_top = get_x_at_y(*right_line, 0)
        cx_bot = (lx_bot + rx_bot) // 2
        cx_top = (lx_top + rx_top) // 2
        return draw_info(
            cx_bot, cx_top, "Sredina",
            angle_left   = angle_of_line(left_line),
            angle_right  = angle_of_line(right_line),
            angle_center = calculate_angle(cx_bot, cx_top, h)
        )

    # Slučaj 2: Srednja zona
    if center_line is not None:
        cx_bot = get_x_at_y(*center_line, h)
        cx_top = get_x_at_y(*center_line, 0)
        return draw_info(
            cx_bot, cx_top, "Centar",
            angle_center = calculate_angle(cx_bot, cx_top, h)
        )

    # Slučaj 3: Samo leva
    if left_line is not None:
        vx, vy, x0, y0 = left_line
        cx_bot = get_x_at_y(vx, vy, x0, y0, h) + TAPE_WIDTH // 2
        cx_top = get_x_at_y(vx, vy, x0, y0, 0) + TAPE_WIDTH // 2
        return draw_info(
            cx_bot, cx_top, "Leva",
            angle_left   = angle_of_line(left_line),
            angle_center = calculate_angle(cx_bot, cx_top, h)
        )

    # Slučaj 4: Samo desna
    if right_line is not None:
        vx, vy, x0, y0 = right_line
        cx_bot = get_x_at_y(vx, vy, x0, y0, h) - TAPE_WIDTH // 2
        cx_top = get_x_at_y(vx, vy, x0, y0, 0) - TAPE_WIDTH // 2
        return draw_info(
            cx_bot, cx_top, "Desna",
            angle_right  = angle_of_line(right_line),
            angle_center = calculate_angle(cx_bot, cx_top, h)
        )

    # Slučaj 5: Ništa nije detektovano
    draw_valid_badge()
    return None


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

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)

    left_line, right_line, center_line = find_tape(lines, original_img.shape[1])

    # Validacija para linija
    is_valid = lines_are_valid(left_line, right_line)

    if not is_valid:
        def angle_from_vertical(line):
            vx, vy, x0, y0 = line
            return abs(np.degrees(np.arctan2(vx, vy))) if vy != 0 else 90.0

        if center_line is not None:
            left_line, right_line = None, None
        elif angle_from_vertical(left_line) < angle_from_vertical(right_line):
            right_line = None
        else:
            left_line = None

    offset = draw_tape(result, left_line, right_line, center_line,
                       original_img.shape[0], is_valid)
    return result, offset, left_line, right_line, center_line


# ── Glavna petlja ──────────────────────────────────────────────────────────────
for i in range(1,154):
    t0 = time.time()
    filename   = f"slika{i}.jpg"
    input_path = os.path.join(input_folder, filename)
    if not os.path.exists(input_path):
        continue

    img = cv2.imread(input_path)
    if img is None:
        continue

    print(f"Obrađujem: {filename}...")

    h, w, _ = img.shape
    cropped = img[0:h, 0:w]

    gray    = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Heatmap
    sobelx    = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    sobely    = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(sobelx, sobely)
    mag_norm  = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
    heatmap   = cv2.applyColorMap(mag_norm, cv2.COLORMAP_JET)
    cv2.imwrite(os.path.join(heatmap_folder, f"heatmap{i}.jpg"), heatmap)

    # Canny + ROI
    edges         = cv2.Canny(blurred, 100, 150)
    edges         = apply_trapezoid_roi(edges)
    kernel        = np.ones((3, 3), np.uint8)
    edges_cleared = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite(os.path.join(canny_folder, f"canny{i}.jpg"), edges_cleared)

    # Detekcija
    final_result, offset, left_line, right_line, center_line = detect_lines(edges_cleared, blurred)
    cv2.imwrite(os.path.join(output_folder, f"slika{i}_final.jpg"), final_result)

    if offset is not None:
        if left_line is not None and right_line is not None:
            status = "TRAKA OK (obe ivice)"
        elif center_line is not None:
            status = "TRAKA OK (centralna linija)"
        elif left_line is not None:
            status = "SAMO LEVA → skreni desno"
        else:
            status = "SAMO DESNA → skreni levo"
        print(f"  → offset: {offset:+d}px | {status}")
    else:
        print(f"  → traka nije detektovana")
    print(f"  → {time.time() - t0:.3f}s")

print(f"\nGotovo!\nRezultati su u: {output_folder}\nOčišćeni Canny u: {canny_folder}\nHeatmape u: {heatmap_folder}")