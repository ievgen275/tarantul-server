from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess


class PostInstallCommand(install):
    def run(self):
        install.run(self)

        subprocess.call(['python3', 'drone_firmware.py'])


setup(
    name='tarantul-server',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'websockets',
        'spidev',
        'gps'
    ],
    cmdclass={
        'install': PostInstallCommand,
    },
    entry_points={
        'console_scripts': [
            'tarantul-server = tarantul_server.drone_firmware:initialisation',  # Вказівка на вашу команду
        ],
    },
)