# 🏎️ ROS2 Robot Car

Robotski automobil baziran na **ROS2** platformi sa dualnom arhitekturom (SBC + MCU).

---

## 🏗️ Arhitektura sistema

Sistem koristi podelu poslova između Raspberry Pi 5 i Arduina radi maksimalne efikasnosti:

| Komponenta | Uloga | Opis |
| :--- | :--- | :--- |
| **Raspberry Pi 5** | **CPU (Master)** | Donosi odluke, obrađuje ROS2 čvorove i šalje instrukcije. |
| **Arduino Nano** | **Controller (Slave)** | Direktna kontrola BLDC motora, Servo motora i čitanje senzora. |



### 🛰️ Komunikacioni Protokol (`fw_pkgs.hpp`)
Komunikacija se vrši preko paketa definisanih u `fw_pkgs.hpp`. 
> [!CAUTION]
> **VAŽNO:** Ovaj fajl postoji na dve lokacije. Ako menjaš strukturu u jednom, **moraš** je promeniti u oba:
> 1. `FW/Arduino_Motoro_Controller` (za Arduino)
> 2. `ROS2/ackibot_ws/src/ackibot_node/src/` (za Raspberry Pi)

* **M2S (Master to Slave):** Komande sa Pi-ja ka Arduinu (motor, servo).
* **S2M (Slave to Master):** Telemetrija sa Arduina ka Pi-ju (senzori, status).

---

## 📂 Ključni Fajlovi

* **Firmware:** `FW/Arduino_Motor_Controller/Arduino_Motor_Controller.ino` (Učitati na Arduino)
* **ROS2 Node:** `ROS2/ackibot_ws/src/ackibot_node/src/fw_node.cpp` (Glavna logika instrukcija)

---

## 🚀 Procedura Pokretanja

Prati ove korake tačnim redosledom kako bi izbegao greške u komunikaciji:

1.  **Power On:** Uključi Raspberry Pi (Interni prekidač).
2.  **Access:** Poveži se na Pi putem **SSH**.
3.  **Scripts:** Pokreni skriptu za joypad
    ```bash
    cd ROS2/ackibot_ws/scripts
    ./mars_joys.sh
    ```
4.  **Controller:** Upali joypad kombinacijom tastera **RB + HOME**.
5.  **Run:** Pokreni glavni proces:
    ```bash
    ./ackibot_run_sbc.sh
    ```
6.  **Motors:** Na samom kraju uključi **eksterni prekidač** za motore.

---

## 📶 Troubleshooting (Wi-Fi Problemi)

Ako se Raspberry Pi ne vidi na mreži:
* Poveži PI na monitor i proveri IP adresu u konzoli.
* **Quick Fix:** Ako ne možeš da mu pristupiš, probaj da **pinguješ svoj PC sa Pi-ja**. To često natera ruter da prepozna uređaj i otvori rutu.

---

## 🛠️ Build Instructions
Detaljna uputstva za kompajliranje i build sistema možeš pronaći na:
👉 [GitHub Repository Build Guide](https://github.com/cxxx1828/ROS2-Robot-Car)

---
