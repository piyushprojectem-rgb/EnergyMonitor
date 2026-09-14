from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(...)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from database import supabase
from schemas import (
    MeasurementCreate,
    BatchMeasurementCreate,
    RelayControlCreate
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Energy Monitor API",
    description="Backend for ESP32 IoT Energy Monitoring System",
    version="1.0.0"
)


# ============================================================
# ESP32 WEBSOCKET CONNECTION
# ============================================================

esp32_websocket: WebSocket | None = None


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "message": "Energy Monitor Backend is running"
    }


# ============================================================
# LOADS
# ============================================================

@app.get("/loads")
def get_loads():

    response = (
        supabase
        .table("loads")
        .select("*")
        .order("channel")
        .execute()
    )

    return response.data


# ============================================================
# CREATE SINGLE MEASUREMENT
# ============================================================

@app.post("/measurements")
def create_measurement(
    measurement: MeasurementCreate
):

    data = {
        "load_id": measurement.load_id,
        "timestamp": measurement.timestamp,
        "voltage_v": measurement.voltage_v,
        "current_a": measurement.current_a,
        "power_w": measurement.power_w,
        "power_factor": measurement.power_factor,
        "relay_state": measurement.relay_state
    }

    response = (
        supabase
        .table("measurements")
        .insert(data)
        .execute()
    )

    if not response.data:

        raise HTTPException(
            status_code=500,
            detail="Failed to insert measurement"
        )

    return {
        "status": "success",
        "message": "Measurement stored",
        "data": response.data[0]
    }


# ============================================================
# CREATE BATCH MEASUREMENTS
# ============================================================

@app.post("/measurements/batch")
def create_batch_measurements(
    batch: BatchMeasurementCreate
):

    data = []

    for measurement in batch.measurements:

        data.append({
            "load_id": measurement.load_id,
            "timestamp": batch.timestamp,
            "voltage_v": measurement.voltage_v,
            "current_a": measurement.current_a,
            "power_w": measurement.power_w,
            "power_factor": measurement.power_factor,
            "relay_state": measurement.relay_state
        })

    if not data:

        raise HTTPException(
            status_code=400,
            detail="No measurements provided"
        )

    response = (
        supabase
        .table("measurements")
        .insert(data)
        .execute()
    )

    if not response.data:

        raise HTTPException(
            status_code=500,
            detail="Failed to insert measurements"
        )

    return {
        "status": "success",
        "message": f"{len(response.data)} measurements stored",
        "data": response.data
    }


# ============================================================
# LATEST MEASUREMENT FOR EACH LOAD
# ============================================================

@app.get("/measurements/latest")
def get_latest_measurements():

    latest = []

    for load_id in [1, 2, 3]:

        response = (
            supabase
            .table("measurements")
            .select("*")
            .eq("load_id", load_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:

            latest.append(response.data[0])

    return latest


# ============================================================
# MEASUREMENT HISTORY
# ============================================================

@app.get("/measurements/history")
def get_measurement_history(
    load_id: int | None = None,
    limit: int = 100
):

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    query = (
        supabase
        .table("measurements")
        .select("*")
        .order("timestamp", desc=True)
        .limit(limit)
    )

    if load_id is not None:

        if load_id < 1 or load_id > 3:

            raise HTTPException(
                status_code=400,
                detail="load_id must be 1, 2, or 3"
            )

        query = query.eq("load_id", load_id)

    response = query.execute()

    return response.data


# ============================================================
# RELAY EVENT HISTORY
# ============================================================

@app.get("/relay-events")
def get_relay_events(
    load_id: int | None = None,
    limit: int = 100
):

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    query = (
        supabase
        .table("relay_events")
        .select("*")
        .order("timestamp", desc=True)
        .limit(limit)
    )

    if load_id is not None:

        if load_id < 1 or load_id > 3:

            raise HTTPException(
                status_code=400,
                detail="load_id must be 1, 2, or 3"
            )

        query = query.eq("load_id", load_id)

    response = query.execute()

    return response.data


# ============================================================
# HOURLY ENERGY
# ============================================================

@app.get("/energy/hourly")
def get_hourly_energy(
    load_id: int | None = None,
    limit: int = 24
):

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    query = (
        supabase
        .table("energy_hourly")
        .select("*")
        .order("hour_start", desc=True)
        .limit(limit)
    )

    if load_id is not None:

        if load_id < 1 or load_id > 3:

            raise HTTPException(
                status_code=400,
                detail="load_id must be 1, 2, or 3"
            )

        query = query.eq("load_id", load_id)

    response = query.execute()

    return response.data


# ============================================================
# DAILY ENERGY
# ============================================================

@app.get("/energy/daily")
def get_daily_energy(
    load_id: int | None = None,
    limit: int = 30
):

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    query = (
        supabase
        .table("energy_daily")
        .select("*")
        .order("day_date", desc=True)
        .limit(limit)
    )

    if load_id is not None:

        if load_id < 1 or load_id > 3:

            raise HTTPException(
                status_code=400,
                detail="load_id must be 1, 2, or 3"
            )

        query = query.eq("load_id", load_id)

    response = query.execute()

    return response.data


# ============================================================
# SET RELAY COMMAND
# ============================================================

@app.post("/relays/{load_id}")
async def set_relay(
    load_id: int,
    command: RelayControlCreate
):

    # --------------------------------------------------------
    # Validate load ID
    # --------------------------------------------------------

    if load_id < 1 or load_id > 3:

        raise HTTPException(
            status_code=400,
            detail="load_id must be 1, 2, or 3"
        )


    # --------------------------------------------------------
    # Store relay command in Supabase
    # --------------------------------------------------------

    data = {
        "load_id": load_id,
        "state": command.state,
        "source": "dashboard"
    }

    response = (
        supabase
        .table("relay_events")
        .insert(data)
        .execute()
    )

    if not response.data:

        raise HTTPException(
            status_code=500,
            detail="Failed to create relay command"
        )


    # --------------------------------------------------------
    # Send command immediately to ESP32
    # --------------------------------------------------------

    if esp32_websocket is not None:

        await esp32_websocket.send_json({

            "type": "relay_command",

            "load_id": load_id,

            "state": command.state,

            "event_id": response.data[0]["id"]

        })

        esp32_status = "sent_to_esp32"

    else:

        esp32_status = "esp32_not_connected"


    # --------------------------------------------------------
    # Return response
    # --------------------------------------------------------

    return {

        "status": "success",

        "message": f"Relay {load_id} command created",

        "esp32_status": esp32_status,

        "data": response.data[0]

    }


# ============================================================
# GET CURRENT RELAY COMMANDS
# ============================================================

@app.get("/relay-commands")
def get_relay_commands():

    response = (
        supabase
        .table("relay_events")
        .select(
            "id,load_id,timestamp,state,source"
        )
        .order("id", desc=True)
        .limit(100)
        .execute()
    )

    latest = {}

    for event in response.data:

        load_id = event["load_id"]

        if load_id not in latest:

            latest[load_id] = event

    return list(latest.values())


# ============================================================
# ESP32 WEBSOCKET
# ============================================================

@app.websocket("/ws/esp32")
async def esp32_websocket_endpoint(
    websocket: WebSocket
):

    global esp32_websocket


    # --------------------------------------------------------
    # Accept ESP32 connection
    # --------------------------------------------------------

    await websocket.accept()

    esp32_websocket = websocket

    print()
    print("==================================================")
    print("ESP32 WebSocket connected.")
    print("==================================================")


    try:

        # ----------------------------------------------------
        # Get latest relay state for each load
        # ----------------------------------------------------

        response = (
            supabase
            .table("relay_events")
            .select(
                "id,load_id,timestamp,state,source"
            )
            .order("id", desc=True)
            .limit(100)
            .execute()
        )


        # ----------------------------------------------------
        # Find latest event for each relay
        # ----------------------------------------------------

        latest = {}

        for event in response.data:

            load_id = event["load_id"]

            if load_id not in latest:

                latest[load_id] = event


        # ----------------------------------------------------
        # Send current relay states to ESP32
        # ----------------------------------------------------

        for event in latest.values():

            await websocket.send_json({

                "type": "relay_command",

                "load_id": event["load_id"],

                "state": event["state"],

                "event_id": event["id"]

            })

            print(
                f"Sent initial relay state: "
                f"Load {event['load_id']} = "
                f"{'ON' if event['state'] else 'OFF'}"
            )


        # ----------------------------------------------------
        # Keep WebSocket connection alive
        # ----------------------------------------------------

        while True:

            message = await websocket.receive_text()

            print(
                "ESP32 message:",
                message
            )


    except WebSocketDisconnect:

        print()
        print("ESP32 WebSocket disconnected.")


    except Exception as e:

        print()
        print(
            "ESP32 WebSocket error:",
            e
        )


    finally:

        if esp32_websocket is websocket:

            esp32_websocket = None

            print(
                "ESP32 WebSocket connection cleared."
            )