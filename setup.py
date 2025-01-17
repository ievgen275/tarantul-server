from setuptools import setup, find_packages

setup(
    name='tarantul-server',
    version='0.1',
    packages=find_packages(),
    install_requires=open('requirements.txt').read().splitlines(),  # Вказуємо залежності з requirements.txt
    entry_points={
        'console_scripts': [
            'tarantul-server=tarantul-server.tarantul-server.drone_firmware:setup',  # точка входу в ваш проєкт
        ],
    },
)