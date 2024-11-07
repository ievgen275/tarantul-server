## 1. Pull this repository
## 2. Make your script executable
`chmod +x /home/pi/myscript.py`
## 3. Create a Systemd Service File
Copy file "drone.service" to the path **'/etc/systemd/system/'** 
## 4. Reload Systemd and Enable Your Service
Reload systemd to recognize the new service and enable it to start on boot.

`sudo systemctl daemon-reload`

`sudo systemctl enable myscript.service`

## 5. Start Your Service
Start your service immediately.

`sudo systemctl start myscript.service`

## 6. Check the Status of Your Service
You can check the status of your service to ensure it is running correctly.

`sudo systemctl status myscript.service`

## 7. Stop Your Service (if needed)
If you need to stop the service at any point, you can do so with the following command:

`sudo systemctl stop myscript.service`

## 8. View Logs
To view logs for your service, you can use **journalctl**

`sudo journalctl -u myscript.service`

