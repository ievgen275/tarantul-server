import gps
import json
import asyncio

latitude = None
longitude = None


async def read_gps(websocket):
    session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

    global latitude, longitude
    while True:
        report = session.next()
        if report("class") == 'TPV':
            latitude = round(getattr(report, 'lat', None), 4)
            longitude = round(getattr(report, 'lon', None), 4)

            if latitude is not None and longitude is not None:
                print(f"Latitude: {latitude}, Longitude: {longitude}")

                data_gps_json = json.dumps({
                    'latitude': latitude,
                    'longitude': longitude
                })
                await websocket.send(data_gps_json)


def start_read_gps(websocket):
    asyncio.run(read_gps(websocket))
