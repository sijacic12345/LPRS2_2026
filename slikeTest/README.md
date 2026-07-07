# line_detection.py — Dokumentacija

## Pregled

Modul za detekciju trake od lepljive trake (selotejp) u realnom vremenu.
Ulaz: BGR frejm sa kamere. Izlaz: anotiran frejm, offset i steering komanda.

```python
result, offset, cmd = detect_lines_logic(frame)
```

---

## Pipeline

```
BGR frejm
    │
    ▼
Grayscale → Gaussian Blur (7x7)
    │
    ▼
Canny (70/100)
    │
    ▼
Trapezoidni ROI
    │
    ▼
HoughLinesP
    │
    ▼
filter_horizontal  — odbacuje linije ispod MIN_ANGLE=10°
    │
    ▼
find_best_tape_pair  — traži par paralelnih linija na udaljenosti TAPE_WIDTH
    │
    ▼
get_cmd  — računa steering komandu na osnovu uglova para
    │
    ▼
(result, offset, cmd)
```

---

## Parametri

| Parametar        | Vrednost | Opis                                              |
|------------------|----------|---------------------------------------------------|
| `TAPE_WIDTH`     | 33 px    | Očekivana širina trake na robotu (640px kadar)    |
| `TAPE_TOL`       | 12 px    | Tolerancija širine trake ±px                      |
| `ANGLE_TOL`      | 15 °     | Max razlika uglova para da bi bile "paralelne"    |
| `MIN_ANGLE`      | 10 °     | Min ugao linije od horizontale (odbacuje fuge)    |
| `CANNY_LO/HI`   | 70/100   | Pragovi Canny detekcije ivica                     |
| `TARGET_WIDTH_PX`| 735 px  | Referentna širina trake za steering kalkulator    |

> **Napomena:** `TAPE_WIDTH` je kalibrisan za RPi kameru (IMX708) na visini ~20cm,
> udaljenost ~30cm, kadar 640px. Za LP batch skripte vrednost se razlikuje.

---

## Trapezoidni ROI

```
  (15%, 30%)------(85%, 30%)
       /                  \
      /                    \
  (0%, 100%)-----------(100%, 100%)
```

Gornja granica ROI-a je na 30% visine kadra.
Isključuje plafon i udaljene delove poda koji unose šum.

---

## Detekcija para — find_best_tape_pair

Za svaki par Hough segmenata proverava:
1. **Paralelnost** — razlika uglova < `ANGLE_TOL` (15°)
2. **Udaljenost** — normalna distanca između segmenata ≈ `TAPE_WIDTH ± TAPE_TOL`

Score = `angle_diff + dist_err * 0.5` — manji score = bolji par.

---

## Steering logika — get_cmd

Koristi ugao svakog segmenta od vertikale (`get_angle_from_seg`).

| Situacija              | l_ang | r_ang | Akcija                        |
|------------------------|-------|-------|-------------------------------|
| Oba pozitivna          | > 0   | > 0   | Skreni desno                  |
| Oba negativna          | < 0   | < 0   | Skreni levo                   |
| V-oblik (greška)       | < 0   | > 0   | Korektan po X poziciji        |
| Lambda (staza ispred)  | > 0   | < 0   | Vozi pravo ili mala korekcija |

`calculate_steering_command` vraća vrednost u opsegu **[-0.4, 0.4]**.

---

## Izlaz

| Vrednost  | Tip   | Opis                                              |
|-----------|-------|---------------------------------------------------|
| `result`  | ndarray | BGR frejm sa vizualizacijom                    |
| `offset`  | int   | Pomak centra trake od centra kadra u px (±)       |
| `cmd`     | float | Steering komanda [-0.4, 0.4] za fw_node           |

### Vizualizacija na frejmu
- 🟢 **Zeleno** — sve Hough linije koje su prošle filter
- 🟠 **Narandžasto** — leva ivica detektovanog para
- 🟣 **Ljubičasto** — desna ivica detektovanog para
- 🔵 **Plavo** — centar trake (odluka)
- 🔴 **Crveno** — centar kamere (referenca)

---

## Integracija

### camera_streamer.py
```python
processed_frame, offset, cmd = detect_lines_logic(frame)
```

### lane_follower_node.py
```python
_, offset, cmd = detect_lines_logic(frame)
msg = Twist()
msg.linear.x  = self.base_speed
msg.angular.z = cmd
self.cmd_pub.publish(msg)
```

---

## Kalibracija TAPE_WIDTH

```
TAPE_WIDTH [px] = (sirina_trake_cm / sirina_kadra_cm) * sirina_kadra_px
```

Za IMX708 (FOV ~66°) na udaljenosti 30cm:
```
sirina_kadra_cm ≈ 2 * 30 * tan(33°) ≈ 39 cm
TAPE_WIDTH = (2 / 39) * 640 ≈ 33 px
```
