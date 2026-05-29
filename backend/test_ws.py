import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8081/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket.")
            
            # Start match
            await websocket.send(json.dumps({
                "type": "start_match",
                "team1": "RR",
                "team2": "SRH"
            }))
            print("Sent start_match")
            
            # Listen to a few events
            events_received = 0
            while events_received < 10:
                response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                data = json.loads(response)
                
                if data["type"] == "ball_result":
                    print(f"Received ball_result: {data['ball']['runs']} runs, Wicket: {data['ball']['is_wicket']}")
                    print(f"Description: {data['ball']['description']}")
                    print(f"Match State: Runs={data['state']['runs']}, Wickets={data['state']['wickets']}, Overs={data['state']['overs']}")
                    events_received += 1
                elif data["type"] == "prediction_window":
                    print("Received prediction_window")
                    # Send a prediction
                    await websocket.send(json.dumps({
                        "type": "predict",
                        "prediction": "dot"
                    }))
                    print("Sent predict: dot")
                elif data["type"] == "match_starting":
                    print("Match starting...")
                else:
                    pass
                    
            print("Successfully received events. Closing connection.")
    except Exception as e:
        print(f"Test failed: {e}")

asyncio.run(test_websocket())
