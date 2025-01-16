import os
import subprocess

SERVICE_NAME = "drone.service"
SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}"

SERVICE_CONTENT = f"""
[Unit]
Description=Drone Firmware
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m tarantul_server.drone_firmware
WorkingDirectory=/home/conceptarea/tarantul-server/
StandardOutput=inherit
StandardError=inherit
Restart=always
User=conceptarea

[Install]
WantedBy=multi-user.target
"""

def install_service():
    # Записуємо сервісний файл
    with open(SERVICE_PATH, "w") as f:
        f.write(SERVICE_CONTENT)
    # Перезапускаємо systemd
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
    subprocess.run(["systemctl", "start", SERVICE_NAME], check=True)
    print(f"Сервіс {SERVICE_NAME} успішно встановлено та запущено.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Будь ласка, запустіть як root.")
    else:
        install_service()