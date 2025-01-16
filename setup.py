from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess

# Клас для виконання додаткових дій після установки
class PostInstallCommand(install):
    def run(self):
        # Виконати стандартний процес установки
        install.run(self)
        # Запуск скрипта для реєстрації systemd-сервісу
        subprocess.run(["python3", "install_daemon.py"])

# Конфігурація пакета
setup(
    name="tarantul-server",
    version="0.1.0",
    description="Daemon for controlling drones on Raspberry Pi",
    author="Ім'я Автора",
    author_email="your_email@example.com",
    url="https://github.com/ievgen275/tarantul-server",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "tarantul-server=tarantul_server.drone_firmware:main",  # Точка входу в основний скрипт
        ]
    },
    cmdclass={  # Підключення кастомної команди
        'install': PostInstallCommand,
    },
)