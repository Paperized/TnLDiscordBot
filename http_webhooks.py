from flask import Flask, request, jsonify
from events import on_event_started
from shared import EVENT_SCHEDULER, create_event_trigger, MIN_DELAY
from datetime import datetime, timedelta

app = Flask(__name__)

# get the record in input from supabase and schedule the event for the bot

@app.route('/new-event', methods=['POST'])
def handle_post():
    # Extract JSON data from the request
    entity_data = request.json.record
    
    # Process the data (you can print or handle it however you like)
    print("Received data:", entity_data)

    event_at = entity_data.event_at

    dt_notification = event_at - timedelta(minutes=MIN_DELAY)
    if dt_notification > datetime.now():
        dt_notification = datetime.now() + timedelta(minutes=1)

    trigger = create_event_trigger(event_at)
    EVENT_SCHEDULER.add_job(on_event_started, trigger, args=[event_at])
    
    # Respond to the client
    return jsonify({"message": "OK"}), 200

app.run(host='0.0.0.0', port=5000, debug=True)
